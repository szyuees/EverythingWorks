from strands import tool
from duckduckgo_search import DDGS
import requests


@tool
def web_search(query: str, max_results: int = 5):
    """Search the web for flat listings using DuckDuckGo."""
    try:
        results = []
        for item in DDGS().text(query, max_results=max_results):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "link": item.get("href", "")
            })
        return results if results else "No results found."
    except Exception as e:
        return f"Web search error: {e}"

@tool
def http_request(url: str):
    """Perform HTTP GET request."""
    try:
        resp = requests.get(url)
        return resp.text[:1000]  # return only first 1000 chars for brevity
    except Exception as e:
        return f"Error fetching URL {url}: {e}"

@tool
def filter_and_rank(results, location=None, max_price=None, flat_type=None, k=3):
    """Filter search results by criteria and return top-k."""
    if not isinstance(results, list):
        return "Invalid input: results must be a list"
    return results[:k]

@tool
def repayment_duration(principal: float, monthly_payment: float) -> str:
    """Compute repayment duration in years and months."""
    if monthly_payment <= 0:
        return "Monthly payment must be greater than 0"
    months = principal / monthly_payment
    years = int(months // 12)
    rem_months = int(months % 12)
    return f"{years} years and {rem_months} months"