import asyncio
import re
from typing import List, Optional

from sqlmodel import select

from app.config import settings
from app.models.listing import Listing
from app.services.db import get_session
from app.utils.budget_parser import parse_budget_to_range
from app.utils.logger import logger

_WORD_TO_DIGIT = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
}


def _normalize_property_type(text: Optional[str]) -> str:
    if not text:
        return ""
    t = text.strip().lower().replace("-", " ")
    for word, digit in _WORD_TO_DIGIT.items():
        t = re.sub(rf"\b{word}\b", digit, t)
    match = re.search(r"(\d+)\s*(bhk|bedrooms|bedroom|beds|bed)\b", t)
    if match:
        return f"{match.group(1)}bhk"
    return re.sub(r"\s+", "", t)


def _parse_bedrooms(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"\d+", str(text))
    return int(match.group()) if match else None


def _location_match(preference: Optional[str], location: Optional[str]) -> bool:
    if not preference or not location:
        return False
    p = preference.strip().lower()
    loc = location.strip().lower()
    if p in loc or loc in p:
        return True
    p_tokens = set(p.replace(",", " ").split())
    loc_tokens = set(loc.replace(",", " ").split())
    return bool(p_tokens & loc_tokens)


def _budget_in_range(budget_text: Optional[str], price_min: Optional[int], price_max: Optional[int]) -> bool:
    caller_min, caller_max = parse_budget_to_range(budget_text)
    if caller_min is None or price_min is None or price_max is None:
        return True  # can't evaluate either side — neutral, don't penalize
    return caller_max >= price_min and caller_min <= price_max


def match_listings(
    preferences: dict,
    listings: List[dict],
    max_results: Optional[int] = None,
    min_score: Optional[int] = None,
) -> List[dict]:
    """Pure function — no I/O, no DB, no network. Scores each listing against caller
    preferences and returns the top matches, sorted best-first."""
    max_results = settings.MAX_LISTINGS_PER_MATCH if max_results is None else max_results
    min_score = settings.LISTING_MATCH_MIN_SCORE if min_score is None else min_score

    pref_type = _normalize_property_type(preferences.get("property_type"))
    pref_location = preferences.get("location_preference")
    pref_bedrooms = _parse_bedrooms(preferences.get("bedrooms"))
    pref_budget_text = preferences.get("budget")

    scored = []
    for listing in listings:
        if listing.get("availability_status") != "available":
            continue

        score = 0
        if _location_match(pref_location, listing.get("location")):
            score += 40
        if pref_type and pref_type == _normalize_property_type(listing.get("property_type")):
            score += 30

        listing_bedrooms = _parse_bedrooms(listing.get("bedrooms"))
        if pref_bedrooms is not None and listing_bedrooms is not None and abs(pref_bedrooms - listing_bedrooms) <= 1:
            score += 15

        if _budget_in_range(pref_budget_text, listing.get("price_min"), listing.get("price_max")):
            score += 15

        if score >= min_score:
            scored.append({**listing, "match_score": score})

    scored.sort(key=lambda item: item["match_score"], reverse=True)
    return scored[:max_results]


def _sync_create_listing(agent_number: str, raw_caption: str, extracted: dict, image_urls: List[str], message_sid: str) -> Listing:
    price_min, price_max = parse_budget_to_range(extracted.get("price_text"))
    listing = Listing(
        agent_number=agent_number,
        raw_caption=raw_caption,
        property_type=extracted.get("property_type"),
        location=extracted.get("location"),
        price_text=extracted.get("price_text"),
        price_min=price_min,
        price_max=price_max,
        bedrooms=extracted.get("bedrooms"),
        furnishing=extracted.get("furnishing"),
        amenities=extracted.get("amenities"),
        image_urls=image_urls,
        listing_summary=extracted.get("listing_summary"),
        availability_status=extracted.get("availability_status") or "available",
        message_sid=message_sid,
    )
    with get_session() as session:
        session.add(listing)
        session.commit()
        session.refresh(listing)
        logger.info(f"Listing created: id={listing.id} location={listing.location}")
        return listing


async def create_listing(agent_number: str, raw_caption: str, extracted: dict, image_urls: List[str], message_sid: str) -> Listing:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _sync_create_listing, agent_number, raw_caption, extracted, image_urls, message_sid
    )


def _sync_get_active_listings() -> List[dict]:
    with get_session() as session:
        results = session.exec(select(Listing).where(Listing.availability_status == "available")).all()
        return [row.model_dump() for row in results]


async def get_active_listings() -> List[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_get_active_listings)
