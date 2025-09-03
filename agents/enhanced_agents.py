# enhanced_agents.py
from strands import Agent, tool
from tools import web_search, http_request
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class RAGEnhancedAgent:
    def __init__(self, collection_name: str, model_name: str = "all-MiniLM-L6-v2"):
        self.client = chromadb.PersistentClient()
        self.collection = self.client.get_or_create_collection(collection_name)
        self.encoder = SentenceTransformer(model_name)
    
    def semantic_search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Perform semantic search in the knowledge base"""
        query_embedding = self.encoder.encode([query])
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k
        )
        return results

@tool
def rag_policy_search(query: str, domain: str = "hdb_policies") -> str:
    """Search Singapore housing policies and regulations using RAG"""
    rag_agent = RAGEnhancedAgent(domain)
    results = rag_agent.semantic_search(query)
    
    if not results['documents']:
        return "No relevant policy information found."
    
    context = "\n".join(results['documents'][0][:3])  # Top 3 results
    return f"Policy Context:\n{context}"

@tool
def rag_grant_eligibility(user_profile: Dict[str, Any]) -> str:
    """Check grant eligibility using structured RAG knowledge"""
    rag_agent = RAGEnhancedAgent("grant_schemes")
    
    # Create semantic query from user profile
    query = f"eligibility {user_profile.get('citizenship')} {user_profile.get('income_range')} {user_profile.get('flat_type')} first time buyer"
    
    results = rag_agent.semantic_search(query, top_k=5)
    
    if not results['documents']:
        return "No eligible grants found."
    
    # Process and rank grants based on user profile
    eligible_grants = []
    for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
        eligible_grants.append({
            'name': metadata.get('grant_name'),
            'amount': metadata.get('amount'),
            'details': doc[:200]
        })
    
    return format_grant_results(eligible_grants)

def format_grant_results(grants: List[Dict]) -> str:
    """Format grant results for user presentation"""
    if not grants:
        return "No eligible grants found."
    
    formatted = "### Your Eligible Housing Grants:\n\n"
    for grant in grants:
        formatted += f"**{grant['name']}**\n"
        formatted += f"Amount: {grant['amount']}\n"
        formatted += f"Details: {grant['details']}\n\n"
    
    return formatted

# Enhanced Grant Agent with RAG
enhanced_grant_agent = Agent(
    system_prompt='''
    You are an enhanced Grant Eligibility Agent with access to comprehensive RAG knowledge base.
    Use rag_policy_search and rag_grant_eligibility tools to provide accurate, up-to-date information.
    
    When a user asks about grants:
    1. Collect user information efficiently (ask once)
    2. Use RAG tools to search relevant grant information
    3. Cross-reference eligibility criteria
    4. Present results clearly with amounts and next steps
    
    Always prioritize official information from your knowledge base over web search.
    Only use web search for very recent policy changes not in your knowledge base.
    ''',
    tools=[rag_policy_search, rag_grant_eligibility, web_search]
)

# Enhanced Property Agent with Market Intelligence
@tool
def rag_market_analysis(location: str, property_type: str, budget_range: str) -> str:
    """Provide market analysis using historical data and trends"""
    rag_agent = RAGEnhancedAgent("market_data")
    
    query = f"{location} {property_type} pricing trends {budget_range}"
    results = rag_agent.semantic_search(query, top_k=3)
    
    if not results['documents']:
        return "Limited market data available for this area."
    
    analysis = "### Market Analysis:\n\n"
    for doc in results['documents'][0]:
        analysis += f"- {doc}\n"
    
    return analysis

@tool  
def rag_location_insights(location: str, user_needs: List[str]) -> str:
    """Provide location insights based on user needs"""
    rag_agent = RAGEnhancedAgent("location_intel")
    
    needs_query = " ".join(user_needs)
    query = f"{location} amenities {needs_query}"
    
    results = rag_agent.semantic_search(query, top_k=5)
    
    insights = f"### {location} - Location Insights:\n\n"
    for doc in results['documents'][0]:
        insights += f"- {doc}\n"
    
    return insights

enhanced_property_agent = Agent(
    system_prompt='''
    You are an enhanced Property Search Agent with comprehensive market intelligence.
    
    Your workflow:
    1. Gather user requirements efficiently
    2. Use rag_market_analysis for pricing and trends
    3. Use rag_location_insights for area-specific information
    4. Use web_search only for current listings
    5. Provide comprehensive recommendations
    
    Always combine RAG insights with real-time search results.
    ''',
    tools=[rag_market_analysis, rag_location_insights, web_search, http_request]
)