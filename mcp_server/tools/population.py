"""
Census Tool — Population
=========================
Retrieves total population data by state or county.

Census variables used:
  B01001_001E  — Total population
  B01002_001E  — Median age
  B11001_001E  — Total households
"""

from .census_client import census_request, resolve_state_fips

# ── Mock data (realistic 2022 ACS estimates) ──────────────────────────────────
MOCK_POPULATIONS = {
    "California":       {"population": 39029342, "median_age": 37.0, "households": 13844930},
    "Texas":            {"population": 30029572, "median_age": 35.5, "households": 10740424},
    "Florida":          {"population": 22244823, "median_age": 42.2, "households": 9079885},
    "New York":         {"population": 19677151, "median_age": 38.7, "households": 7564243},
    "Pennsylvania":     {"population": 12972008, "median_age": 40.8, "households": 5220124},
    "Illinois":         {"population": 12582032, "median_age": 38.7, "households": 4844696},
    "Ohio":             {"population": 11756058, "median_age": 39.6, "households": 4719346},
    "Georgia":          {"population": 10912876, "median_age": 37.3, "households": 4053813},
    "North Carolina":   {"population": 10698973, "median_age": 39.0, "households": 4256396},
    "Michigan":         {"population": 10034113, "median_age": 40.0, "households": 3983169},
    "Washington":       {"population": 7785786,  "median_age": 37.8, "households": 3008310},
    "Virginia":         {"population": 8683619,  "median_age": 38.6, "households": 3367003},
    "Arizona":          {"population": 7359197,  "median_age": 38.5, "households": 2832697},
    "Massachusetts":    {"population": 6981974,  "median_age": 39.6, "households": 2699100},
    "Colorado":         {"population": 5773714,  "median_age": 37.0, "households": 2275342},
    "Tennessee":        {"population": 7051339,  "median_age": 39.0, "households": 2800576},
    "Indiana":          {"population": 6785528,  "median_age": 37.9, "households": 2646292},
    "Missouri":         {"population": 6177957,  "median_age": 39.2, "households": 2455892},
    "Maryland":         {"population": 6164660,  "median_age": 38.8, "households": 2330467},
    "Wisconsin":        {"population": 5895908,  "median_age": 40.3, "households": 2329669},
    "Minnesota":        {"population": 5717184,  "median_age": 38.3, "households": 2256308},
    "Oregon":           {"population": 4246155,  "median_age": 39.9, "households": 1707017},
    "Nevada":           {"population": 3177772,  "median_age": 38.3, "households": 1200498},
    "Utah":             {"population": 3380800,  "median_age": 31.3, "households": 1133946},
    "New Mexico":       {"population": 2113344,  "median_age": 38.6, "households": 808283},
    "Wyoming":          {"population": 581381,   "median_age": 37.6, "households": 230419},
    "Vermont":          {"population": 647464,   "median_age": 43.1, "households": 261127},
    "District of Columbia": {"population": 671803, "median_age": 34.4, "households": 308350},
    "United States":    {"population": 333287557, "median_age": 38.9, "households": 124487536},
}


def get_population(geography: str, state: str = None, county: str = None) -> dict:
    """
    Get population statistics for a state, county, or the full US.

    Args:
        geography: "state", "county", or "us"
        state: State name or abbreviation (required for state/county)
        county: County name (required for county geography)

    Returns dict with population, median_age, households, and source metadata.
    """

    # ── Mock mode ─────────────────────────────────────────────────────────────
    from config import MOCK_MODE
    if MOCK_MODE:
        if geography == "us" or (state and state.lower() in ("us", "united states", "usa")):
            data = MOCK_POPULATIONS["United States"]
            name = "United States"
        else:
            # Find best match in mock data
            search = (state or "").title()
            data = MOCK_POPULATIONS.get(search)
            if not data:
                # Try partial match
                matches = [k for k in MOCK_POPULATIONS if search.lower() in k.lower()]
                if matches:
                    name = matches[0]
                    data = MOCK_POPULATIONS[name]
                else:
                    return {"error": f"No mock data for '{state}'. Try: California, Texas, New York, Florida, etc."}
            else:
                name = search

        return {
            "geography": name,
            "population": data["population"],
            "median_age": data["median_age"],
            "households": data["households"],
            "year": "2022",
            "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022 [MOCK DATA]",
        }

    # ── Live Census API ───────────────────────────────────────────────────────
    variables = ["B01001_001E", "B01002_001E", "B11001_001E"]

    if geography == "us":
        results = census_request(variables, "us")
        geo_label = "United States"

    elif geography == "state":
        fips = resolve_state_fips(state)
        if not fips:
            return {"error": f"Could not find state: '{state}'. Try the full state name or 2-letter abbreviation."}
        results = census_request(variables, "state", fips)
        geo_label = state.title()

    elif geography == "county":
        if not state or not county:
            return {"error": "Both 'state' and 'county' are required for county-level queries."}
        fips = resolve_state_fips(state)
        if not fips:
            return {"error": f"Could not find state: '{state}'"}
        results = census_request(variables, "county", f"*&in=state:{fips}")
        if isinstance(results, dict) and "error" in results:
            return results
        # Filter to matching county
        county_results = [r for r in results if county.lower() in r.get("NAME", "").lower()]
        if not county_results:
            return {"error": f"Could not find county '{county}' in {state}."}
        results = county_results
        geo_label = county.title()

    else:
        return {"error": f"Unknown geography type: '{geography}'. Use 'state', 'county', or 'us'."}

    if isinstance(results, dict) and "error" in results:
        return results

    row = results[0]
    return {
        "geography": row.get("NAME", geo_label),
        "population": int(row.get("B01001_001E", 0)),
        "median_age": float(row.get("B01002_001E", 0)),
        "households": int(row.get("B11001_001E", 0)),
        "year": "2022",
        "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022",
    }
