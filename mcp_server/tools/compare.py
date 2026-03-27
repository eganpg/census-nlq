"""
Census Tool — State Comparison
================================
Compares population and income metrics across multiple states.
Useful for questions like "which state has the highest income?"
or "compare California and Texas".
"""

from .population import get_population
from .income import get_income


def compare_states(states: list[str], metric: str = "all") -> dict:
    """
    Compare multiple states on population, income, and poverty metrics.

    Args:
        states: List of state names or abbreviations
        metric: "population", "income", "poverty", or "all"

    Returns a ranked comparison table.
    """
    results = []

    for state in states:
        entry = {"state": state.title()}

        if metric in ("population", "all"):
            pop = get_population("state", state=state)
            if "error" not in pop:
                entry["population"] = pop["population"]
                entry["median_age"] = pop["median_age"]

        if metric in ("income", "poverty", "all"):
            inc = get_income("state", state=state)
            if "error" not in inc:
                entry["median_household_income"] = inc["median_household_income"]
                entry["poverty_rate_pct"] = inc["poverty_rate_pct"]
                entry["unemployment_rate_pct"] = inc["unemployment_rate_pct"]

        results.append(entry)

    # Sort by the primary metric
    sort_key = {
        "population": "population",
        "income":     "median_household_income",
        "poverty":    "poverty_rate_pct",
        "all":        "population",
    }.get(metric, "population")

    results.sort(key=lambda x: x.get(sort_key, 0), reverse=True)

    return {
        "comparison": results,
        "sorted_by": sort_key,
        "states_compared": len(results),
        "year": "2022",
        "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022",
    }


def get_national_ranking(state: str, metric: str) -> dict:
    """
    Find where a state ranks nationally on a given metric.
    Uses mock data for all 50 states + DC.
    """
    from .population import MOCK_POPULATIONS
    from .income import MOCK_INCOME
    from config import MOCK_MODE

    # For ranking we always use mock (live would be 51 API calls)
    if metric == "population":
        all_data = {k: v["population"] for k, v in MOCK_POPULATIONS.items()
                    if k != "United States"}
    elif metric == "income":
        all_data = {k: v["median_income"] for k, v in MOCK_INCOME.items()
                    if k != "United States"}
    elif metric == "poverty":
        all_data = {k: v["poverty_rate"] for k, v in MOCK_INCOME.items()
                    if k != "United States"}
    else:
        return {"error": f"Unknown metric '{metric}'. Use 'population', 'income', or 'poverty'"}

    search = state.title()
    # Partial match
    matches = [k for k in all_data if search.lower() in k.lower()]
    if not matches:
        return {"error": f"State '{state}' not found"}

    state_name = matches[0]
    state_value = all_data[state_name]

    ranked = sorted(all_data.items(), key=lambda x: x[1], reverse=(metric != "poverty"))
    rank = next((i + 1 for i, (k, _) in enumerate(ranked) if k == state_name), None)

    return {
        "state": state_name,
        "metric": metric,
        "value": state_value,
        "rank": rank,
        "out_of": len(ranked),
        "top_3": [{"state": k, "value": v} for k, v in ranked[:3]],
        "bottom_3": [{"state": k, "value": v} for k, v in ranked[-3:]],
        "year": "2022",
        "source": "U.S. Census Bureau, ACS 5-Year Estimates 2022",
    }
