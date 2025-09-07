# agents/orchestrator_agent.py - Updated to use consolidated tools
from strands import Agent, tool
import logging
from aws_session import session

logger = logging.getLogger(__name__)

# Import consolidated tools
try:
    from tools_consolidated import (
        web_search, singapore_housing_search, property_search, 
        filter_and_rank_properties, calculate_affordability,
        enhanced_http_request, tool_registry
    )
    CONSOLIDATED_TOOLS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Consolidated tools not available: {e}")
    # Fallback to old tools during transition
    from tools import enhanced_web_search as web_search, singapore_housing_search, property_search
    CONSOLIDATED_TOOLS_AVAILABLE = False

# Import agents with error handling
try:
    from agents.property_agent import property_agent
    from agents.grant_agent import grant_agent
    from agents.filter_agent import filter_agent
    from agents.writer_agent import writer_agent
except ImportError as e:
    logging.warning(f"Agent import error: {e}")
    property_agent = grant_agent = filter_agent = writer_agent = None

# AWS RAG tools
try:
    from ragtool.aws_rag_tools import aws_rag_search, singapore_housing_aws_search
    AWS_RAG_AVAILABLE = True
except ImportError:
    AWS_RAG_AVAILABLE = False

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

# Consolidated tool wrappers for backward compatibility
@tool
def enhanced_property_search(query: str, max_results: int = 6):
    """Enhanced property search using consolidated tools"""
    if CONSOLIDATED_TOOLS_AVAILABLE:
        return property_search(query, max_results)
    else:
        # Fallback to old implementation
        return property_search(query, max_results)

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
        return f"AWS RAG search error: {str(e)}. Using web search fallback."

@tool
def validate_system_status():
    """Validate system status and available tools"""
    if CONSOLIDATED_TOOLS_AVAILABLE:
        try:
            from tools_consolidated import get_tool_status
            return get_tool_status()
        except:
            return "Tool status checking unavailable"
    else:
        return "Using legacy tools - consolidated tools not available"

# Get available tools for the orchestrator
if CONSOLIDATED_TOOLS_AVAILABLE:
    available_tools = [
        call_property_agent, call_grant_agent, call_filter_agent, call_writer_agent,
        enhanced_property_search, web_search, singapore_housing_search,
        calculate_affordability, enhanced_http_request, smart_rag_search, validate_system_status
    ]
else:
    # Fallback tool list for transition period
    from tools import enhanced_web_search, calculate_affordability, http_request
    available_tools = [
        call_property_agent, call_grant_agent, call_filter_agent, call_writer_agent,
        enhanced_web_search, singapore_housing_search, calculate_affordability,
        http_request, smart_rag_search, validate_system_status
    ]

# Enhanced orchestrator with comprehensive error handling
orchestrator = Agent(
    system_prompt=f"""
You are an enhanced Housing Chatbot Orchestrator for Singapore housing assistance.

System Status: {'✅ Using consolidated tools' if CONSOLIDATED_TOOLS_AVAILABLE else '⚠️ Using legacy tools'}
AWS RAG: {'✅ Available' if AWS_RAG_AVAILABLE else '❌ Unavailable'}

Available capabilities:
- Property search and recommendations: call_property_agent, enhanced_property_search
- Grant eligibility assessment: call_grant_agent  
- Property filtering and ranking: call_filter_agent
- Financial calculations and formatting: call_writer_agent
{'- AWS Knowledge Base search: smart_rag_search' if AWS_RAG_AVAILABLE else ''}
{'- System status validation: validate_system_status' if CONSOLIDATED_TOOLS_AVAILABLE else ''}

Decision flow:
1. For policy/regulation questions -> Use smart_rag_search (AWS Knowledge Base)
2. For grant eligibility -> Use call_grant_agent (with AWS KB support)
3. For property search -> Use enhanced_property_search or call_property_agent 
4. For filtering/ranking -> Use call_filter_agent
5. For calculations and formatting -> Use call_writer_agent

**Property Search Guidelines:**
- Always use enhanced_property_search for initial property searches
- Output **only JSON** for property listings when requested
- Each listing must include:
    {{
      "name": "property name",
      "block_number": "block number", 
      "street_name": "street name",
      "price": 0,
      "rooms": 0,
      "location": "location",
      "floor": 0,
      "amenities": ["list of amenities"],
      "ranking_reason": "reason for ranking",
      "link": "VALIDATED working URL"
    }}
- Ensure URLs are validated and accessible
- After JSON, provide brief human-readable summary

**Error Handling:**
- Always provide helpful responses even if some tools are unavailable
- If AWS Knowledge Base is unavailable, fall back to web search
- For web searches, include source URLs and verify information accuracy
- Handle tool failures gracefully and suggest alternatives
- Be conversational while maintaining accuracy

**Response Format:**
- Include conversation summary and decisions made
- Always cite information sources
- Explain reasoning behind recommendations
- Provide actionable next steps when appropriate

**Tool Usage Priority:**
1. Use consolidated tools when available (more efficient)
2. Fall back to legacy tools during transition
3. Always validate tool responses before presenting to user
4. Log any tool failures for debugging
""",
    tools=available_tools
)

# System initialization check
def initialize_orchestrator():
    """Initialize orchestrator with system checks"""
    try:
        status_msg = f"Orchestrator initialized - Consolidated tools: {CONSOLIDATED_TOOLS_AVAILABLE}, AWS RAG: {AWS_RAG_AVAILABLE}"
        logger.info(status_msg)
        
        if CONSOLIDATED_TOOLS_AVAILABLE:
            tool_status = validate_system_status()
            logger.info(f"Tool status: {tool_status}")
        
        return orchestrator
    except Exception as e:
        logger.error(f"Orchestrator initialization error: {e}")
        return orchestrator

# Initialize on import
orchestrator = initialize_orchestrator()