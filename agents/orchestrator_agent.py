# agents/orchestrator_agent.py - Fixed import dependencies for new repo structure
from strands import Agent, tool
import logging

logger = logging.getLogger(__name__)

# Import consolidated tools with comprehensive fallbacks
CONSOLIDATED_TOOLS_AVAILABLE = False
AWS_RAG_AVAILABLE = False
DECISION_AGENT_AVAILABLE = False

# Try consolidated tools first
try:
    from tools_consolidated import (
        web_search, singapore_housing_search, property_search, 
        filter_and_rank_properties, calculate_affordability,
        enhanced_http_request, get_tool_status
    )
    CONSOLIDATED_TOOLS_AVAILABLE = True
    logger.info("Consolidated tools imported successfully")
except ImportError as e:
    logger.warning(f"Consolidated tools not available: {e}")
    # Set tools to None for safety
    web_search = singapore_housing_search = property_search = None
    filter_and_rank_properties = calculate_affordability = None
    enhanced_http_request = get_tool_status = None

# Try AWS tools
try:
    from tools_consolidated.aws import (
        aws_rag_search, singapore_housing_aws_search, validate_aws_rag_configuration
    )
    AWS_RAG_AVAILABLE = True
    logger.info("AWS RAG tools imported successfully")
except ImportError as e:
    logger.warning(f"AWS RAG tools not available: {e}")
    aws_rag_search = singapore_housing_aws_search = validate_aws_rag_configuration = None

# Try external tools
try:
    from tools_consolidated.external import search_property_portals
    EXTERNAL_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"External tools not available: {e}")
    search_property_portals = None
    EXTERNAL_TOOLS_AVAILABLE = False

# Import agents with error handling
try:
    from agents.property_agent import property_agent
    from agents.grant_agent import grant_agent
    from agents.filter_agent import filter_agent
    from agents.writer_agent import writer_agent
    AGENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some agents not available: {e}")
    property_agent = grant_agent = filter_agent = writer_agent = None
    AGENTS_AVAILABLE = False

# Try decision agent
try:
    from agents.decision_agent import decision_agent
    DECISION_AGENT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Decision agent not available: {e}")
    decision_agent = None

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

# Enhanced agent wrappers
@tool
def call_property_agent(query: str):
    """Call property agent for property search and listings"""
    return safe_agent_call(property_agent, query)

@tool
def call_grant_agent(query: str):
    """Call grant agent for eligibility assessment"""
    return safe_agent_call(grant_agent, query)

@tool
def call_filter_agent(query: str):
    """Call filter agent for property filtering and ranking"""
    return safe_agent_call(filter_agent, query)

@tool
def call_writer_agent(query: str):
    """Call writer agent for formatting and financial calculations"""
    return safe_agent_call(writer_agent, query)

@tool
def call_decision_agent(query: str):
    """Call decision agent for comprehensive property analysis"""
    if DECISION_AGENT_AVAILABLE and decision_agent:
        return safe_agent_call(decision_agent, query)
    else:
        return "Decision analysis agent not available. Use individual property and financial tools instead."

# Consolidated tool wrappers with enhanced functionality
@tool
def enhanced_property_search(query: str, max_results: int = 6):
    """Enhanced property search using consolidated portal search"""
    try:
        if CONSOLIDATED_TOOLS_AVAILABLE and search_property_portals:
            return search_property_portals(query, max_results=max_results)
        elif CONSOLIDATED_TOOLS_AVAILABLE and property_search:
            return property_search(query, max_results)
        else:
            return [{"error": "Property search tools not available"}]
    except Exception as e:
        logger.error(f"Enhanced property search error: {e}")
        return [{"error": f"Property search error: {str(e)}"}]

@tool
def smart_rag_search(query: str):
    """Intelligent RAG search using AWS Knowledge Base with fallbacks"""
    try:
        # Determine domain based on query content
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['grant', 'cpf', 'subsidy', 'eligible']):
            domain = "grant_schemes"
        elif any(word in query_lower for word in ['hdb', 'policy', 'regulation', 'eligibility']):
            domain = "hdb_policies"  
        elif any(word in query_lower for word in ['price', 'market', 'trend', 'value']):
            domain = "market_data"
        else:
            domain = "hdb_policies"
        
        # Try AWS RAG first
        if AWS_RAG_AVAILABLE and singapore_housing_aws_search:
            result = singapore_housing_aws_search(query, domain)
            if result and "error" not in str(result).lower():
                return result
        
        # Fallback to regular Singapore housing search
        if CONSOLIDATED_TOOLS_AVAILABLE and singapore_housing_search:
            search_type = "grants" if domain == "grant_schemes" else "policies"
            return singapore_housing_search(query, search_type=search_type)
        else:
            return "RAG search not available - missing dependencies"
        
    except Exception as e:
        logger.error(f"Smart RAG search error: {e}")
        return f"RAG search error: {str(e)}"

@tool
def validate_system_tools():
    """Validate system status and available tools"""
    try:
        if CONSOLIDATED_TOOLS_AVAILABLE and get_tool_status:
            status = get_tool_status()
            available_tools = status.get('available_tools', 0)
            total_tools = status.get('total_tools', 0)
            
            status_report = f"System Status: {available_tools}/{total_tools} tools available\n"
            
            # Add category breakdown
            categories = status.get('categories', {})
            for category, info in categories.items():
                available_count = len(info.get('available', []))
                unavailable_count = len(info.get('unavailable', []))
                status_report += f"- {category}: {available_count} available, {unavailable_count} unavailable\n"
                
                # List unavailable tools
                for unavailable in info.get('unavailable', []):
                    status_report += f"  ! {unavailable['name']}: {unavailable['error']}\n"
            
            return status_report
        else:
            return f"Tool registry not available - Consolidated: {CONSOLIDATED_TOOLS_AVAILABLE}, AWS: {AWS_RAG_AVAILABLE}, Agents: {AGENTS_AVAILABLE}"
            
    except Exception as e:
        logger.error(f"System validation error: {e}")
        return f"System validation failed: {str(e)}"

@tool
def comprehensive_affordability_analysis(monthly_income: float, existing_debt: float = 0, 
                                       deposit_saved: float = 0):
    """Enhanced affordability analysis using consolidated financial tools"""
    try:
        if not CONSOLIDATED_TOOLS_AVAILABLE or not calculate_affordability:
            return "Affordability calculation not available - missing financial tools"
            
        result = calculate_affordability(monthly_income, existing_debt, deposit_saved)
        
        if isinstance(result, dict):
            # Format the detailed response
            analysis = f"""
**Affordability Analysis for ${monthly_income:,.0f} monthly income:**

- **Max Monthly Payment**: ${result.get('max_monthly_payment', 0):,.0f}
- **Estimated Budget Range**: {result.get('estimated_budget_range', 'N/A')}
- **Income Utilization**: {result.get('income_utilization', 'N/A')}
- **TDSR Utilization**: {result.get('tdsr_utilization', 'N/A')}
- **HDB Eligible**: {'Yes' if result.get('hdb_eligible', False) else 'No'}

**Property Types Available**: {', '.join(result.get('property_types', ['Unknown']))}

**Recommendations**:
"""
            recommendations = result.get('recommendations', [])
            for i, rec in enumerate(recommendations, 1):
                analysis += f"{i}. {rec}\n"
                
            return analysis
        else:
            return str(result)
            
    except Exception as e:
        logger.error(f"Affordability analysis error: {e}")
        return f"Affordability analysis failed: {str(e)}"

# Build available tools list based on what's imported successfully
available_tools = [
    validate_system_tools  # Always available
]

# Add agent tools if available
if AGENTS_AVAILABLE:
    available_tools.extend([
        call_property_agent, call_grant_agent, call_filter_agent, call_writer_agent
    ])

# Add decision agent if available
if DECISION_AGENT_AVAILABLE:
    available_tools.append(call_decision_agent)

# Add consolidated tools if available
if CONSOLIDATED_TOOLS_AVAILABLE:
    available_tools.extend([
        enhanced_property_search, comprehensive_affordability_analysis
    ])
    
    if web_search:
        available_tools.append(web_search)
    if singapore_housing_search:
        available_tools.append(singapore_housing_search)
    if enhanced_http_request:
        available_tools.append(enhanced_http_request)

# Add AWS tools if available
if AWS_RAG_AVAILABLE:
    available_tools.extend([smart_rag_search])
    if validate_aws_rag_configuration:
        available_tools.append(validate_aws_rag_configuration)

# Enhanced orchestrator with comprehensive capabilities
orchestrator = Agent(
    system_prompt=f"""
You are an enhanced Housing Chatbot Orchestrator for Singapore housing assistance.

**System Status**: 
- Consolidated Tools: {'✅ Active' if CONSOLIDATED_TOOLS_AVAILABLE else '❌ Not Available'}
- AWS RAG: {'✅ Available' if AWS_RAG_AVAILABLE else '❌ Not Available'}
- Decision Analysis: {'✅ Available' if DECISION_AGENT_AVAILABLE else '❌ Not Available'}
- Agent System: {'✅ Available' if AGENTS_AVAILABLE else '❌ Not Available'}

**CRITICAL WORKFLOW RULES:**
1. NEVER call both enhanced_property_search AND call_property_agent for the same query
2. For property search queries, use ONLY ONE of these approaches:
   - Enhanced search: Use enhanced_property_search directly
   - Agent search: Use call_property_agent (which internally uses property_search)
3. Choose the enhanced_property_search for direct property listings
4. Choose call_property_agent only for complex property analysis needs

**Decision Flow:**
1. For policy/regulation questions → Use smart_rag_search (if available)
2. For grant eligibility → Use call_grant_agent (if available)
3. For simple property search → Use enhanced_property_search ONLY
4. For complex property analysis → Use call_property_agent ONLY (not both)
5. For filtering/ranking existing results → Use call_filter_agent (if available)
6. For financial calculations → Use comprehensive_affordability_analysis or call_writer_agent
7. For comprehensive property analysis → Use call_decision_agent (if available)

**Property Search Guidelines:**
- For direct property listing requests: Use enhanced_property_search and stop
- Output **only JSON** for property listings when requested
- Each listing must include:
    {
      "name": "property name",
      "snippet": "property description", 
      "url": "property URL",
      "price": 0,
      "rooms": 0,
      "location": "location",
      "ranking_reason": "reason for ranking"
    }
- After JSON, provide brief human-readable summary
- Do NOT call multiple search tools for the same query

**Error Handling & Fallbacks:**
- If enhanced_property_search fails, then try call_property_agent
- Always provide helpful responses even if tools are unavailable
- If AWS Knowledge Base fails, inform user of limitation
- Handle tool failures gracefully and suggest alternatives
- Be transparent about system limitations

**Response Format:**
- Include conversation summary and decisions made
- Always cite information sources when available
- Explain reasoning behind recommendations
- Provide actionable next steps
- Highlight any system limitations or tool unavailability

**Quality Assurance:**
- Prioritize official Singapore government sources when possible
- Validate financial calculations when tools are available
- Provide realistic timelines and expectations
- Consider Singapore-specific regulations (TDSR, CPF usage, citizenship requirements)
""",
    tools=available_tools
)

def initialize_orchestrator():
    """Initialize orchestrator with comprehensive system checks"""
    try:
        status_msg = f"Orchestrator initialized with {len(available_tools)} tools"
        logger.info(status_msg)
        
        # Log tool availability
        if CONSOLIDATED_TOOLS_AVAILABLE:
            logger.info("✅ Using consolidated tools")
        else:
            logger.warning("⚠️ Consolidated tools not available")
        
        if DECISION_AGENT_AVAILABLE:
            logger.info("✅ Decision analysis agent available")
        else:
            logger.warning("⚠️ Decision agent not available")
        
        if AWS_RAG_AVAILABLE:
            logger.info("✅ AWS RAG search available")
        else:
            logger.warning("⚠️ AWS RAG not available")
            
        if AGENTS_AVAILABLE:
            logger.info("✅ Agent system available")
        else:
            logger.warning("⚠️ Agent system not available")
        
        return orchestrator
        
    except Exception as e:
        logger.error(f"Orchestrator initialization error: {e}")
        return orchestrator

# Initialize on import
orchestrator = initialize_orchestrator()