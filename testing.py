#!/usr/bin/env python3
"""
Housing Chatbot using Strands + Hugging Face T5 + DuckDuckGo

Features:
- Dynamic web search for flats using DuckDuckGo
- Filter & rank top-k results
- Optional repayment duration calculation
- Multi-agent workflow: Property Search -> Filter & Rank -> Writer
- Uses CPU-compatible libraries for Windows
"""
python -m venv .venv
source .venv/bin/activate
pip install strands-agents strands-agents-tools



import logging
import requests
from strands import Agent, tool
from duckduckgo_search import DDGS
from transformers import pipeline

# --- Logging ---
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Using DuckDuckGo for web search and Hugging Face T5 for reasoning")

# --- Hugging Face T5 Pipeline ---
hf_pipeline = pipeline(
    "text2text-generation",
    model="google/t5gemma-b-b-prefixlm",
    device=-1  # CPU only on Windows
)

# Wrapper to make HF pipeline compatible with Strands Agent
class HFModelWrapper:
    def __init__(self, pipeline):
        self.pipeline = pipeline

    def __call__(self, prompt):
        output = self.pipeline(prompt, max_length=512, do_sample=False)
        return output[0]['generated_text']

hf_agent_model = HFModelWrapper(hf_pipeline)

# --- Tools ---
@tool
def web_search(query: str, max_results: int = 5):
    """Search the web for flat listings using DuckDuckGo."""
    results = []
    for item in DDGS().text(query, max_results=max_results):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("body", ""),
            "link": item.get("href", "")
        })
    return results

@tool
def http_request(url: str):
    """Perform HTTP GET request."""
    try:
        resp = requests.get(url)
        return resp.text
    except Exception as e:
        return f"Error fetching URL {url}: {e}"

@tool
def filter_and_rank(results, location=None, max_price=None, flat_type=None, k=3):
    """Filter search results by criteria and return top-k."""
    # For simplicity, just return the first k results
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

# --- Agents ---
property_agent = Agent(
    model=hf_agent_model,
    system_prompt="You are a Property Search Agent. Find web listings for flats.",
    tools=[web_search, http_request]
)

filter_agent = Agent(
    model=hf_agent_model,
    system_prompt="You are a Filter & Rank Agent. Filter listings by user criteria and return top-k.",
    tools=[filter_and_rank]
)

writer_agent = Agent(
    model=hf_agent_model,
    system_prompt="You are a Writer Agent. Format top-k listings and optionally include repayment info.",
    tools=[repayment_duration]
)

# Orchestrator Agent
orchestrator = Agent(
    model=hf_agent_model,
    system_prompt="""
    You are a Housing Chatbot orchestrator.
    Decide which agents to call based on the user's query:
    - Property search -> property_agent
    - Filtering & ranking -> filter_agent
    - Repayment calculation -> writer_agent
    Return a final, clear response for the user.
    """,
    tools=[property_agent, filter_agent, writer_agent]
)

# --- Main Loop ---
if __name__ == "__main__":
    print("\nWelcome to Housing Chatbot!")
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
