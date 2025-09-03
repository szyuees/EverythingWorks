from strands import Agent, tool
from agents.property_agent import property_agent
from agents.grant_agent import grant_agent
from agents.filter_agent import filter_agent
from agents.writer_agent import writer_agent
# Import new tools
from tools import rag_search, initialize_rag_system


@tool
def call_property_agent(query: str):
    return property_agent(query)

@tool
def call_grant_agent(query: str):
    return grant_agent(query)

@tool
def call_filter_agent(query: str):
    return filter_agent(query)

@tool
def call_writer_agent(query: str):
    return writer_agent(query)

## New RAG-based tools
@tool
def smart_rag_search(query: str):
    """Intelligent RAG search across knowledge domains"""
    
    # Determine which knowledge domain to search
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['grant', 'cpf', 'subsidy', 'eligible']):
        domain = "grant_schemes"
    elif any(word in query_lower for word in ['hdb', 'policy', 'regulation', 'eligibility']):
        domain = "hdb_policies"  
    elif any(word in query_lower for word in ['price', 'market', 'trend', 'value']):
        domain = "market_data"
    else:
        domain = "hdb_policies"  # Default
    
    return rag_search(query, domain)

# Enhanced orchestrator with RAG capabilities
orchestrator = Agent(
    system_prompt="""
    You are an enhanced Housing Chatbot orchestrator with RAG knowledge base access.
    
    Decision flow:
    1. For policy/regulation questions -> Use smart_rag_search first, then relevant agent
    2. For grant eligibility -> Use smart_rag_search + call_grant_agent  
    3. For property search -> Use smart_rag_search for market context + call_property_agent
    4. For filtering/ranking -> call_filter_agent
    5. For calculations -> call_writer_agent
    
    Always combine RAG knowledge with real-time web search for comprehensive answers.
    """,
    tools=[
        call_property_agent, 
        call_filter_agent, 
        call_writer_agent, 
        call_grant_agent,
        smart_rag_search,
        initialize_rag_system
    ]
)