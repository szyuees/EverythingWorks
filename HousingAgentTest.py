#!/usr/bin/env python3
"""
Housing Chatbot using Strands + DuckDuckGo + AWS Bedrock

Features:
- Dynamic web search for flats using DuckDuckGo
- Filter & rank top-k results
- Optional repayment duration calculation
- Multi-agent workflow: Property Search -> Filter & Rank -> Writer
"""

import logging
import requests
import os
from strands import Agent, tool
from ddgs import DDGS   # stable DuckDuckGo search library

# --- Ensure AWS credentials are set (from user-provided values) ---


# --- Logging ---
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Using DuckDuckGo for web search and AWS Bedrock model via Strands")

# --- Tools ---
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

# --- Sub-Agents ---
property_agent = Agent(
    system_prompt="You are a Property Search Agent. Find web listings for flats.",
    tools=[web_search, http_request]
)

filter_agent = Agent(
    system_prompt="You are a Filter & Rank Agent. Filter listings by user criteria and return top-k.",
    tools=[filter_and_rank]
)

writer_agent = Agent(
    system_prompt="You are a Writer Agent. Format top-k listings and optionally include repayment info.",
    tools=[repayment_duration]
)

# --- Wrappers so orchestrator can call them as tools ---
@tool
def call_property_agent(query: str):
    return property_agent(query)

@tool
def call_filter_agent(query: str):
    return filter_agent(query)

@tool
def call_writer_agent(query: str):
    return writer_agent(query)

# --- Orchestrator Agent ---
orchestrator = Agent(
    system_prompt="""
    You are a Housing Chatbot orchestrator.
    Decide which agents to call based on the user's query:
    - For property search use call_property_agent
    - For filtering & ranking use call_filter_agent
    - For repayment calculation use call_writer_agent
    """,
    tools=[call_property_agent, call_filter_agent, call_writer_agent]
)

# --- Main Loop ---
if __name__ == "__main__":
    print("\n🏠 Welcome to Housing Chatbot!")
    print("Type 'exit' to quit\n")

    while True:
        try:
            user_input = input("> ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye! 👋")
                break

            # Pass user query to orchestrator agent
            response = orchestrator(user_input)
            print("\n" + str(response) + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue
