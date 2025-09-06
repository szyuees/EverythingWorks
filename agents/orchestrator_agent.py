from strands import Agent, tool
import logging
from aws_session import session

# Import agents with error handling
try:
    from agents.property_agent import property_agent
    from agents.grant_agent import grant_agent
    from agents.filter_agent import filter_agent
    from agents.writer_agent import writer_agent
except ImportError as e:
    logging.warning(f"Agent import error: {e}")
    property_agent = grant_agent = filter_agent = writer_agent = None

# Import new tools with error handling
try:
    from ragtool.aws_rag_tools import (
        aws_rag_search, 
        singapore_housing_aws_search,
        validate_aws_rag_configuration
    )
    AWS_RAG_AVAILABLE = True
except ImportError as e:
    logging.warning(f"AWS RAG tools not available: {e}")
    AWS_RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

def safe_agent_call(agent, query):
    """Safely call an agent and return string response"""
    try:
        if agent is None:
            return "Agent not available"
        
        result = agent(query)
        
        # Handle different types of agent responses
        if hasattr(result, 'content'):
            return str(result.content)
        elif hasattr(result, 'text'):
            return str(result.text)
        elif hasattr(result, 'message'):
            return str(result.message)
        else:
            return str(result)
    except Exception as e:
        logger.error(f"Agent call error: {e}")
        return f"Error calling agent: {str(e)}"

@tool
def call_property_agent(query: str):
    """Call property agent with error handling"""
    return safe_agent_call(property_agent, query)

@tool
def call_grant_agent(query: str):
    """Call grant agent with error handling"""
    return safe_agent_call(grant_agent, query)

@tool
def call_filter_agent(query: str):
    """Call filter agent with error handling"""
    return safe_agent_call(filter_agent, query)

@tool
def call_writer_agent(query: str):
    """Call writer agent with error handling"""
    return safe_agent_call(writer_agent, query)

# RAG-based tools with error handling
@tool
def smart_rag_search(query: str):
    """Intelligent RAG search using AWS Knowledge Base"""
    
    if not AWS_RAG_AVAILABLE:
        return "AWS RAG search not available. Using web search fallback."
    
    try:
        # Determine domain based on query
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['grant', 'cpf', 'subsidy', 'eligible']):
            domain = "grant_schemes"
        elif any(word in query_lower for word in ['hdb', 'policy', 'regulation', 'eligibility']):
            domain = "hdb_policies"  
        elif any(word in query_lower for word in ['price', 'market', 'trend', 'value']):
            domain = "market_data"
        else:
            domain = "hdb_policies"
        
        return singapore_housing_aws_search(query, domain)
    
    except Exception as e:
        logger.error(f"AWS RAG search error: {e}")
        return f"AWS RAG search error: {str(e)}. Please try a web search instead."

@tool
def safe_initialize_rag_system():
    """Validate AWS RAG system configuration"""
    if not AWS_RAG_AVAILABLE:
        return "AWS RAG system not available"
    
    try:
        result = validate_aws_rag_configuration()
        return str(result)
    except Exception as e:
        logger.error(f"AWS RAG validation error: {e}")
        return f"AWS RAG validation failed: {str(e)}"

# Enhanced orchestrator with comprehensive error handling
available_tools = [
    call_property_agent, 
    call_filter_agent, 
    call_writer_agent, 
    call_grant_agent
]

# Add RAG tools if available
if AWS_RAG_AVAILABLE:
    available_tools.extend([smart_rag_search, safe_initialize_rag_system])

orchestrator = Agent(
    system_prompt=f"""
    You are an enhanced Housing Chatbot orchestrator for Singapore housing assistance.
    
    Available capabilities:
    - Property search and recommendations: call_property_agent
    - Grant eligibility assessment: call_grant_agent  
    - Property filtering and ranking: call_filter_agent
    - Financial calculations and formatting: call_writer_agent
    {'- AWS Knowledge Base search: smart_rag_search' if AWS_RAG_AVAILABLE else ''}
    {'- AWS RAG system validation: safe_initialize_rag_system' if AWS_RAG_AVAILABLE else ''}
    
    Decision flow:
    1. For policy/regulation questions -> Use smart_rag_search (AWS Knowledge Base)
    2. For grant eligibility -> Use call_grant_agent (with AWS KB support)
    3. For property search -> Use call_property_agent 
    4. For filtering/ranking -> Use call_filter_agent
    5. For calculations and formatting -> Use call_writer_agent
    
    Always provide helpful responses even if some tools are unavailable.
    If AWS Knowledge Base is unavailable, fall back to web search. For web search, use official sources like HDB, CPF, or gov.sg.
    For web search, always output the source URLs used, and ensure information is accurate and up-to-date.
    When calling the agents, handle any errors gracefully and inform the user if a tool is unavailable, always follow specific output format as declared by the agent.
    If an agent call fails, inform the user and suggest alternative actions. 
    
    Be conversational and helpful while being accurate with Singapore housing information.
    """,
    tools=available_tools
)