"""
Census API client — shared utilities for all Census tools.

Handles:
  - Building API URLs
  - Making requests with/without an API key
  - Normalizing responses
  - Mock data fallback for development
"""

import json
import urllib.request
import urllib.parse
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from config import CENSUS_BASE_URL, CENSUS_YEAR, CENSUS_DATASET, CENSUS_API_KEY, MOCK_MODE

# ── State FIPS code lookup ────────────────────────────────────────────────────
STATE_FIPS = {
    "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05",
    "california": "06", "colorado": "08", "connecticut": "09", "delaware": "10",
    "florida": "12", "georgia": "13", "hawaii": "15", "idaho": "16",
    "illinois": "17", "indiana": "18", "iowa": "19", "kansas": "20",
    "kentucky": "21", "louisiana": "22", "maine": "23", "maryland": "24",
    "massachusetts": "25", "michigan": "26", "minnesota": "27", "mississippi": "28",
    "missouri": "29", "montana": "30", "nebraska": "31", "nevada": "32",
    "new hampshire": "33", "new jersey": "34", "new mexico": "35", "new york": "36",
    "north carolina": "37", "north dakota": "38", "ohio": "39", "oklahoma": "40",
    "oregon": "41", "pennsylvania": "42", "rhode island": "44", "south carolina": "45",
    "south dakota": "46", "tennessee": "47", "texas": "48", "utah": "49",
    "vermont": "50", "virginia": "51", "washington": "53", "west virginia": "54",
    "wisconsin": "55", "wyoming": "56", "district of columbia": "11",
    # Abbreviations
    "al":"01","ak":"02","az":"04","ar":"05","ca":"06","co":"08","ct":"09",
    "de":"10","fl":"12","ga":"13","hi":"15","id":"16","il":"17","in":"18",
    "ia":"19","ks":"20","ky":"21","la":"22","me":"23","md":"24","ma":"25",
    "mi":"26","mn":"27","ms":"28","mo":"29","mt":"30","ne":"31","nv":"32",
    "nh":"33","nj":"34","nm":"35","ny":"36","nc":"37","nd":"38","oh":"39",
    "ok":"40","or":"41","pa":"42","ri":"44","sc":"45","sd":"46","tn":"47",
    "tx":"48","ut":"49","vt":"50","va":"51","wa":"53","wv":"54","wi":"55",
    "wy":"56","dc":"11",
}

def resolve_state_fips(state: str) -> Optional[str]:
    """Convert a state name or abbreviation to FIPS code."""
    return STATE_FIPS.get(state.lower().strip())

def census_request(variables: list[str], geo: str, geo_id: str = "*") -> list[dict]:
    """
    Make a request to the Census API.
    Returns a list of dicts with variable names as keys.
    Falls back to mock data if MOCK_MODE=true or if the request fails.
    """
    if MOCK_MODE:
        return None  # caller handles mock

    url = (
        f"{CENSUS_BASE_URL}/{CENSUS_YEAR}/{CENSUS_DATASET}"
        f"?get=NAME,{','.join(variables)}&for={geo}:{geo_id}"
    )
    if CENSUS_API_KEY:
        url += f"&key={CENSUS_API_KEY}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "census-nlq/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e), "tip": "Run with MOCK_MODE=true for offline testing"}

    # First row is headers, rest are data
    headers = data[0]
    return [dict(zip(headers, row)) for row in data[1:]]
