from app.services.listing_service import match_listings
from app.utils.budget_parser import parse_budget_to_range


def _listing(**overrides):
    base = {
        "id": 1,
        "property_type": "2BHK",
        "location": "Velachery",
        "price_text": "80 lakhs",
        "price_min": 8000000,
        "price_max": 8000000,
        "bedrooms": "2",
        "availability_status": "available",
    }
    base.update(overrides)
    return base


PREFERENCES = {
    "property_type": "2BHK",
    "location_preference": "Velachery",
    "budget": "80 lakhs",
    "bedrooms": "2",
}


def test_parse_budget_to_range_single_value():
    assert parse_budget_to_range("80 lakhs") == (8000000, 8000000)


def test_parse_budget_to_range_range_with_units_on_each_side():
    assert parse_budget_to_range("50L-70L") == (5000000, 7000000)


def test_parse_budget_to_range_crore():
    assert parse_budget_to_range("1.2 crore") == (12000000, 12000000)


def test_parse_budget_to_range_unparsable():
    assert parse_budget_to_range("asdkjhasd") == (None, None)
    assert parse_budget_to_range(None) == (None, None)
    assert parse_budget_to_range("") == (None, None)


def test_exact_match_scores_highest():
    exact = _listing(id=1)
    partial = _listing(id=2, location="Adyar", property_type="3BHK")
    results = match_listings(PREFERENCES, [partial, exact])

    assert results[0]["id"] == 1
    assert results[0]["match_score"] == 100


def test_no_candidates_returns_empty_list():
    assert match_listings(PREFERENCES, []) == []


def test_no_matching_listings_returns_empty_list():
    unrelated = _listing(id=9, location="Whitefield", property_type="Villa", bedrooms="5",
                          price_min=50000000, price_max=60000000)
    assert match_listings(PREFERENCES, [unrelated]) == []


def test_unavailable_listings_are_excluded():
    sold = _listing(id=3, availability_status="sold")
    assert match_listings(PREFERENCES, [sold]) == []


def test_budget_affects_score_between_otherwise_identical_listings():
    in_budget = _listing(id=1, price_min=8000000, price_max=8000000)
    out_of_budget = _listing(id=2, price_min=50000000, price_max=60000000)
    results = match_listings(PREFERENCES, [in_budget, out_of_budget])

    scores = {r["id"]: r["match_score"] for r in results}
    assert scores[1] == 100
    assert scores[2] == 85  # loses the 15-point budget component


def test_case_insensitive_location_match():
    listing = _listing(id=1, location="VELACHERY, Chennai")
    results = match_listings(PREFERENCES, [listing])
    assert len(results) == 1
    assert results[0]["id"] == 1


def test_respects_max_results_cap():
    listings = [_listing(id=i) for i in range(5)]
    results = match_listings(PREFERENCES, listings, max_results=2)
    assert len(results) == 2
