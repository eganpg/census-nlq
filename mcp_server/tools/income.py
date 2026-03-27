"""
Census Tool — Income & Poverty
================================
Retrieves economic data by state or county.

Census variables:
  B19013_001E  — Median household income
  B17001_002E  — Population below poverty level
  B01001_001E  — Total population (for poverty rate calculation)
  B23025_005E  — Unemployed (civilian labor force)
  B23025_003E  — Civilian labor force
"""

from .census_client import census_request, resolve_state_fips

MOCK_INCOME = {
    "California":       {"median_income": 84907,  "poverty_rate": 11.4, "unemployment_rate": 4.9},
    "Texas":            {"median_income": 67321,  "poverty_rate": 14.2, "unemployment_rate": 4.2},
    "Florida":          {"median_income": 61777,  "poverty_rate": 13.1, "unemployment_rate": 3.8},
    "New York":         {"median_income": 75157,  "poverty_rate": 13.0, "unemployment_rate": 5.1},
    "Pennsylvania":     {"median_income": 67587,  "poverty_rate": 11.4, "unemployment_rate": 4.4},
    "Illinois":         {"median_income": 72205,  "poverty_rate": 11.5, "unemployment_rate": 5.2},
    "Ohio":             {"median_income": 62262,  "poverty_rate": 13.0, "unemployment_rate": 4.3},
    "Georgia":          {"median_income": 65030,  "poverty_rate": 14.5, "unemployment_rate": 3.9},
    "North Carolina":   {"median_income": 62891,  "poverty_rate": 14.0, "unemployment_rate": 3.7},
    "Michigan":         {"median_income": 63202,  "poverty_rate": 13.5, "unemployment_rate": 4.5},
    "Washington":       {"median_income": 87648,  "poverty_rate": 10.0, "unemployment_rate": 4.3},
    "Virginia":         {"median_income": 83774,  "poverty_rate": 10.0, "unemployment_rate": 3.3},
    "Arizona":          {"median_income": 65913,  "poverty_rate": 13.4, "unemployment_rate": 4.0},
    "Massachusetts":    {"median_income": 89026,  "poverty_rate": 10.3, "unemployment_rate": 4.3},
    "Colorado":         {"median_income": 82935,  "poverty_rate": 9.8,  "unemployment_rate": 3.6},
    "Tennessee":        {"median_income": 59695,  "poverty_rate": 14.7, "unemployment_rate": 3.6},
    "Indiana":          {"median_income": 63783,  "poverty_rate": 12.0, "unemployment_rate": 3.4},
    "Missouri":         {"median_income": 63348,  "poverty_rate": 12.9, "unemployment_rate": 3.5},
    "Maryland":         {"median_income": 94384,  "poverty_rate": 9.0,  "unemployment_rate": 3.9},
    "Wisconsin":        {"median_income": 69943,  "poverty_rate": 10.4, "unemployment_rate": 3.2},
    "Minnesota":        {"median_income": 80441,  "poverty_rate": 9.5,  "unemployment_rate": 3.3},
    "Oregon":           {"median_income": 73032,  "poverty_rate": 12.0, "unemployment_rate": 4.4},
    "Nevada":           {"median_income": 66274,  "poverty_rate": 12.7, "unemployment_rate": 5.0},
    "Utah":             {"median_income": 79449,  "poverty_rate": 8.7,  "unemployment_rate": 2.8},
    "Mississippi":      {"median_income": 49111,  "poverty_rate": 19.6, "unemployment_rate": 4.5},
    "Louisiana":        {"median_income": 54216,  "poverty_rate": 18.6, "unemployment_rate": 4.8},
    "West Virginia":    {"median_income": 48037,  "poverty_rate": 17.1, "unemployment_rate": 4.8},
    "New Mexico":       {"median_income": 53992,  "poverty_rate": 18.5, "unemployment_rate": 5.1},
    "Wyoming":          {"median_income": 70042,  "poverty_rate": 10.1, "unemployment_rate": 3.7},
    "District of Columbia": {"median_income": 101722, "poverty_rate": 13.4, "unemployment_rate": 6.3},
    "United States":    {"median_income": 74755,  "poverty_rate": 12.6, "unemployment_rate": 4.3},
}


def get_income(geography: str, state: str = None, county: str = None) -> dict:
    """
    Get income, poverty, and unemployment data for a geography.
    """
    from config import MOCK_MODE

    # ── Mock mode ─────────────────────────────────────────────────────────────
    if MOCK_MODE:
        if geography == "us" or (state and state.lower() in ("us", "united states")):
            data = MOCK_INCOME["United States"]
            name = "United States"
        else:
            search = (state or "").title()
            data = MOCK_INCOME.get(search)
            if not data:
                matches = [k for k in MOCK_INCOME if search.lower() in k.lower()]
                if matches:
                    name = matches[0]
                    data = MOCK_INCOME[name]
                else:
                    return {"error": f"No mock data for '{state}'. Try California, Texas, New York, etc."}
            else:
                name = search

        return {
            "geography": name,
            "median_household_income": data["median_income"],
            "poverty_rate_pct": data["poverty_rate"],
            "unemployment_rate_pct": data["unemployment_rate"],
            "year": "2022",
            "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022 [MOCK DATA]",
        }

    # ── Live Census API ───────────────────────────────────────────────────────
    variables = ["B19013_001E", "B17001_002E", "B01001_001E", "B23025_005E", "B23025_003E"]

    if geography == "us":
        results = census_request(variables, "us")
    elif geography == "state":
        fips = resolve_state_fips(state)
        if not fips:
            return {"error": f"Could not find state: '{state}'"}
        results = census_request(variables, "state", fips)
    elif geography == "county":
        fips = resolve_state_fips(state)
        if not fips:
            return {"error": f"Could not find state: '{state}'"}
        results = census_request(variables, "county", f"*&in=state:{fips}")
        if isinstance(results, dict) and "error" in results:
            return results
        results = [r for r in results if county.lower() in r.get("NAME", "").lower()]
        if not results:
            return {"error": f"Could not find county '{county}' in {state}"}
    else:
        return {"error": f"Unknown geography: '{geography}'"}

    if isinstance(results, dict) and "error" in results:
        return results

    row = results[0]
    total_pop   = int(row.get("B01001_001E", 1))
    in_poverty  = int(row.get("B17001_002E", 0))
    unemployed  = int(row.get("B23025_005E", 0))
    labor_force = int(row.get("B23025_003E", 1))

    return {
        "geography": row.get("NAME", state),
        "median_household_income": int(row.get("B19013_001E", 0)),
        "poverty_rate_pct": round(in_poverty / total_pop * 100, 1) if total_pop else None,
        "unemployment_rate_pct": round(unemployed / labor_force * 100, 1) if labor_force else None,
        "year": "2022",
        "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022",
    }
