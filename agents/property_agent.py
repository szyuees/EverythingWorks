# agents/property_agent.py - Fixed import dependencies for new repo structure
from strands import Agent

# Import consolidated tools with fallbacks
CONSOLIDATED_TOOLS_AVAILABLE = False
property_search = filter_and_rank_properties = validate_urls = None

try:
    from tools_consolidated.property import property_search, filter_and_rank_properties
    from tools_consolidated.http import validate_urls
    CONSOLIDATED_TOOLS_AVAILABLE = True
except ImportError:
    try:
        # Ultimate fallback - create minimal implementations
        from typing import List, Dict, Any
        
        def property_search(query: str, max_results: int = 6, sites: List[str] = None):
            return [{"error": "Property search not available - missing dependencies"}]
        
        def filter_and_rank_properties(results, location=None, max_price=None, flat_type=None, k=3):
            return results[:k] if isinstance(results, list) else []
        
        def validate_urls(listings):
            return listings
            
        CONSOLIDATED_TOOLS_AVAILABLE = False
    except Exception:
        CONSOLIDATED_TOOLS_AVAILABLE = False

property_agent = Agent(
    system_prompt=f''' 
    Role: You are a Property Search Agent that searches for properties in Singapore. 

    **System Status**: {'Using consolidated tools' if CONSOLIDATED_TOOLS_AVAILABLE else 'Using fallback mode - limited functionality'}

    **CRITICAL: You MUST output only valid and accessible links for EXACT, ACCURATE, UP-TO-DATE property listings.**
    
    Use enhanced property_search tool for real-time data from:
    - site:propertyguru.com.sg 
    - site:99.co 
    - site:hdb.gov.sg 
    - site:edgeprop.sg 

    Instructions: Before searching the web, gather all necessary information from the user in a single prompt. 
    The information you need includes:
      - What type of flat are you looking to buy? (e.g., HDB, EC, Private) 
      - What is your budget range?
      - How many rooms are you looking for? 
      - What is your preferred location or neighborhood? 
      - What floor level do you prefer? 
      - Do you need to be near public transport (e.g., MRT, bus stops)? 
      - Are there any amenities you would like to have near your home? (e.g., polyclinics, supermarkets, gyms, schools) 
      
    **IMPORTANT Instructions for Output:** 
    1. **FOLLOW THE BELOW FORMAT STRICTLY** 
    - Each listing MUST have the following fields: 
      "name": "property name", 
      "snippet": "property description",
      "url": "property URL", 
      "price": 0, 
      "rooms": 0, 
      "location": "location", 
      "ranking_reason": "reason why this property is ranked this way"
    - The **url must be a valid, accessible URL** pointing DIRECTLY to the property listing on 99.co, PropertyGuru, HDB resale site, or EdgeProp. 
    
    **Example Output Format:** 
    [
      {{
        "name": "3-Room HDB Sengkang Central", 
        "snippet": "Well-maintained 3-room flat in central location", 
        "url": "https://www.99.co/singapore/sale/property/272b-sengkang-central-hdb-Q8WfCvb8kHywz5KpZKnKxc",
        "price": 500000, 
        "rooms": 3, 
        "location": "Sengkang", 
        "ranking_reason": "Excellent value within budget, centrally located with good transport access"
      }}
    ]

    **Workflow:**
    1. Use property_search() to get real-time listings
    2. Use filter_and_rank_properties() to filter and rank results
    3. Use validate_urls() to ensure working links (if available)
    4. Output JSON array with validated property listings
    5. After JSON, provide a brief human-readable summary

    **Error Handling:**
    - If property_search fails, inform user and suggest alternative search terms
    - If no properties match criteria, return empty array []
    - Always validate URLs before including in output when tools are available
    - Handle tool availability gracefully
    - If tools are unavailable, inform user of limitations and suggest manual search
    ''',
    tools=[property_search, filter_and_rank_properties, validate_urls] 
)