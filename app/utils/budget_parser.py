import re
from typing import Optional, Tuple

_UNIT_MULTIPLIERS = {
    "cr": 10_000_000, "crore": 10_000_000, "crores": 10_000_000,
    "l": 100_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
}

_UNIT = r"(cr|crore|crores|lakhs|lakh|lacs|lac|l)"

_RANGE_RE = re.compile(
    rf"(\d+(?:\.\d+)?)\s*{_UNIT}?\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*{_UNIT}",
    re.IGNORECASE,
)
_SINGLE_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*{_UNIT}", re.IGNORECASE)
_BARE_NUMBER_RE = re.compile(r"^\d+$")


def parse_budget_to_range(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None

    cleaned = text.strip().lower()
    cleaned = cleaned.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").strip()

    range_match = _RANGE_RE.search(cleaned)
    if range_match:
        low_val, low_unit, high_val, high_unit = range_match.groups()
        unit = high_unit
        low_unit = low_unit or unit
        low = int(float(low_val) * _UNIT_MULTIPLIERS[low_unit])
        high = int(float(high_val) * _UNIT_MULTIPLIERS[unit])
        return (low, high) if low <= high else (high, low)

    single_match = _SINGLE_RE.search(cleaned)
    if single_match:
        val, unit = single_match.groups()
        amount = int(float(val) * _UNIT_MULTIPLIERS[unit])
        return amount, amount

    bare = cleaned.replace(",", "").replace(" ", "")
    if _BARE_NUMBER_RE.match(bare) and len(bare) >= 4:
        amount = int(bare)
        return amount, amount

    return None, None
