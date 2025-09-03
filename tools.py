from strands import tool
from duckduckgo_search import DDGS
import requests

# new imports for RAG tools
import chromadb
from sentence_transformers import SentenceTransformer
import os

#new tools for RAG
@tool
def initialize_rag_system():
    """Initialize RAG knowledge base on first run"""
    try:
        client = chromadb.PersistentClient(path="./data/vector_store")
        
        # Create collections if they don't exist
        collections = ["hdb_policies", "grant_schemes", "market_data", "location_intel"]
        
        for collection_name in collections:
            try:
                collection = client.get_collection(collection_name)
                print(f"Collection {collection_name} already exists")
            except:
                collection = client.create_collection(collection_name)
                print(f"Created collection {collection_name}")
                
        return "RAG system initialized successfully"
    except Exception as e:
        return f"RAG initialization error: {e}"

@tool  
def rag_search(query: str, collection_name: str = "hdb_policies", top_k: int = 3):
    """Search RAG knowledge base"""
    try:
        client = chromadb.PersistentClient(path="./data/vector_store")
        collection = client.get_collection(collection_name)
        
        # For initial testing, return placeholder
        # You'll populate this with real data later
        return f"RAG Search Results for '{query}' in {collection_name}: [Placeholder - populate with actual HDB/CPF data]"
        
    except Exception as e:
        return f"RAG search error: {e}"
    
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