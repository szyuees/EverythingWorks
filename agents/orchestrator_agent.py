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
    from tools import rag_search, initialize_rag_system
    RAG_AVAILABLE = True
except ImportError as e:
    logging.warning(f"RAG tools not available: {e}")
    RAG_AVAILABLE = False

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
    """Intelligent RAG search across knowledge domains with error handling"""
    
    if not RAG_AVAILABLE:
        return "RAG search not available. Using web search fallback."
    
    try:
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
        
        # Ensure rag_search result is properly handled
        result = rag_search(query, domain)
        
        # Convert any AgentResult to string
        if hasattr(result, 'content'):
            return str(result.content)
        elif hasattr(result, 'text'):
            return str(result.text)
        else:
            return str(result)
    
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return f"RAG search error: {str(e)}. Please try a web search instead."

@tool
def safe_initialize_rag_system():
    """Initialize RAG system with error handling"""
    if not RAG_AVAILABLE:
        return "RAG system not available"
    
    try:
        result = initialize_rag_system()
        return str(result)
    except Exception as e:
        logger.error(f"RAG initialization error: {e}")
        return f"RAG initialization failed: {str(e)}"

# Enhanced orchestrator with comprehensive error handling
available_tools = [
    call_property_agent, 
    call_filter_agent, 
    call_writer_agent, 
    call_grant_agent
]

# Add RAG tools if available
if RAG_AVAILABLE:
    available_tools.extend([smart_rag_search, safe_initialize_rag_system])

orchestrator = Agent(
    system_prompt=f"""
    You are an enhanced Housing Chatbot orchestrator for Singapore housing assistance.
    
    Available capabilities:
    - Property search and recommendations: call_property_agent
    - Grant eligibility assessment: call_grant_agent  
    - Property filtering and ranking: call_filter_agent
    - Financial calculations and formatting: call_writer_agent
    {'- RAG knowledge base search: smart_rag_search' if RAG_AVAILABLE else ''}
    {'- RAG system initialization: safe_initialize_rag_system' if RAG_AVAILABLE else ''}
    
    Decision flow:
    1. For policy/regulation questions -> Use smart_rag_search first (if available), then relevant agent
    2. For grant eligibility -> Use call_grant_agent (with RAG support if available)
    3. For property search -> Use call_property_agent 
    4. For filtering/ranking existing results -> Use call_filter_agent
    5. For calculations and report formatting -> Use call_writer_agent
    
    Always provide helpful responses even if some tools are unavailable.
    If an agent call fails, acknowledge the error and provide general guidance.
    
    Be conversational and helpful while being accurate with Singapore housing information.
    """,
    tools=available_tools
)