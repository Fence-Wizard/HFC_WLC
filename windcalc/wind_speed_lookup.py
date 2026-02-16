"""ZIP code to ASCE 7-22 wind speed lookup.

Provides approximate design wind speeds based on US ZIP code prefix
(first 3 digits). Values are for Risk Category II; the caller should
use the ASCE 7-22 wind maps for the actual risk category.

This is an estimation aid only. The user should always verify the
wind speed from project drawings or the ASCE 7-22 hazard maps.

Data derived from ASCE 7-22 Figures 26.5-1A through 26.5-1D and
the ATC Hazards by Location tool.
"""

from __future__ import annotations

# ── Wind speed regions by ZIP prefix ────────────────────────────────
# Format: {zip_prefix: (wind_speed_risk_II_mph, region_name)}
# These are approximate. Coastal areas may vary significantly
# within the same prefix.

_ZIP_WIND_MAP: dict[str, tuple[int, str]] = {}

# Florida (high wind)
for p in range(320, 340):
    _ZIP_WIND_MAP[str(p)] = (150, "Florida")
for p in [330, 331, 332, 333, 334]:
    _ZIP_WIND_MAP[str(p)] = (170, "South Florida Coast")
for p in [339]:
    _ZIP_WIND_MAP[str(p)] = (160, "Florida Keys")

# Gulf Coast (TX, LA, MS, AL)
for p in range(700, 715):
    _ZIP_WIND_MAP[str(p)] = (130, "Louisiana")
for p in range(770, 780):
    _ZIP_WIND_MAP[str(p)] = (130, "Texas Gulf Coast")
for p in range(780, 800):
    _ZIP_WIND_MAP[str(p)] = (115, "Texas Interior")
for p in range(386, 398):
    _ZIP_WIND_MAP[str(p)] = (120, "Mississippi")
for p in range(350, 370):
    _ZIP_WIND_MAP[str(p)] = (115, "Alabama")

# Southeast Atlantic coast
for p in range(270, 290):
    _ZIP_WIND_MAP[str(p)] = (130, "North Carolina Coast")
for p in range(290, 300):
    _ZIP_WIND_MAP[str(p)] = (130, "South Carolina")
for p in range(300, 320):
    _ZIP_WIND_MAP[str(p)] = (120, "Georgia")

# Virginia / Mid-Atlantic
for p in range(220, 247):
    _ZIP_WIND_MAP[str(p)] = (115, "Virginia")
for p in range(230, 237):
    _ZIP_WIND_MAP[str(p)] = (125, "Virginia Tidewater")
for p in range(200, 220):
    _ZIP_WIND_MAP[str(p)] = (115, "DC / Maryland")
for p in range(206, 219):
    _ZIP_WIND_MAP[str(p)] = (115, "Maryland")

# Northeast
for p in range(100, 150):
    _ZIP_WIND_MAP[str(p)] = (110, "New York")
for p in range(150, 200):
    _ZIP_WIND_MAP[str(p)] = (105, "Pennsylvania")
for p in range(10, 70):
    _ZIP_WIND_MAP[str(p)] = (115, "New England")
for p in range(70, 90):
    _ZIP_WIND_MAP[str(p)] = (110, "New Jersey / Connecticut")

# Midwest / Central
for p in range(400, 430):
    _ZIP_WIND_MAP[str(p)] = (105, "Kentucky")
for p in range(430, 460):
    _ZIP_WIND_MAP[str(p)] = (105, "Ohio")
for p in range(460, 480):
    _ZIP_WIND_MAP[str(p)] = (105, "Indiana")
for p in range(480, 500):
    _ZIP_WIND_MAP[str(p)] = (105, "Michigan")
for p in range(500, 530):
    _ZIP_WIND_MAP[str(p)] = (105, "Iowa / Minnesota")
for p in range(530, 550):
    _ZIP_WIND_MAP[str(p)] = (105, "Wisconsin")
for p in range(550, 570):
    _ZIP_WIND_MAP[str(p)] = (105, "Minnesota")
for p in range(570, 590):
    _ZIP_WIND_MAP[str(p)] = (115, "South Dakota")
for p in range(590, 600):
    _ZIP_WIND_MAP[str(p)] = (105, "Montana")
for p in range(600, 630):
    _ZIP_WIND_MAP[str(p)] = (105, "Illinois")
for p in range(630, 660):
    _ZIP_WIND_MAP[str(p)] = (105, "Missouri")
for p in range(660, 680):
    _ZIP_WIND_MAP[str(p)] = (115, "Kansas")
for p in range(680, 700):
    _ZIP_WIND_MAP[str(p)] = (115, "Nebraska")

# Mountain West
for p in range(800, 840):
    _ZIP_WIND_MAP[str(p)] = (110, "Colorado / Wyoming")
for p in range(840, 850):
    _ZIP_WIND_MAP[str(p)] = (105, "Utah")
for p in range(850, 870):
    _ZIP_WIND_MAP[str(p)] = (105, "Arizona")
for p in range(870, 885):
    _ZIP_WIND_MAP[str(p)] = (110, "New Mexico")

# Pacific West
for p in range(900, 935):
    _ZIP_WIND_MAP[str(p)] = (95, "California (Southern)")
for p in range(935, 970):
    _ZIP_WIND_MAP[str(p)] = (95, "California (Northern)")
for p in range(970, 980):
    _ZIP_WIND_MAP[str(p)] = (95, "Oregon")
for p in range(980, 995):
    _ZIP_WIND_MAP[str(p)] = (95, "Washington")

# Alaska / Hawaii
for p in range(995, 1000):
    _ZIP_WIND_MAP[str(p)] = (120, "Alaska")
_ZIP_WIND_MAP["967"] = (105, "Hawaii")
_ZIP_WIND_MAP["968"] = (130, "Hawaii (Windward)")

# Risk category multipliers (approximate scale from Risk Cat II base)
_RISK_MULTIPLIER: dict[str, float] = {
    "I": 0.87,
    "II": 1.00,
    "III": 1.10,
    "IV": 1.15,
}


def lookup_wind_speed(
    zip_code: str,
    risk_category: str = "II",
) -> tuple[int | None, str]:
    """Look up approximate ASCE 7-22 wind speed from ZIP code.

    Parameters
    ----------
    zip_code : str
        US 5-digit ZIP code.
    risk_category : str
        Risk category (I, II, III, IV).

    Returns
    -------
    tuple[int | None, str]
        ``(wind_speed_mph, region_name)`` or ``(None, "Unknown region")``
        if the ZIP prefix is not in the database.
    """
    if not zip_code or len(zip_code) < 3:
        return None, "Invalid ZIP code"

    prefix = zip_code[:3]
    entry = _ZIP_WIND_MAP.get(prefix)
    if entry is None:
        return None, "ZIP code region not in database"

    base_speed, region = entry
    mult = _RISK_MULTIPLIER.get(risk_category, 1.0)
    adjusted_speed = round(base_speed * mult)

    return adjusted_speed, region


__all__ = ["lookup_wind_speed"]
