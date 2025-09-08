# tools_consolidated/search/search_tools.py - Fixed with updated ddgs import
import logging
from typing import List, Dict, Any, Optional
from strands import tool

logger = logging.getLogger(__name__)

# Import AWS tools with fallback
AWS_RAG_AVAILABLE = False
try:
    from tools_consolidated.aws import aws_rag_search, singapore_housing_aws_search
    AWS_RAG_AVAILABLE = True
    logger.info("AWS RAG tools loaded from consolidated location")
except ImportError:
    logger.warning("AWS RAG tools not available from consolidated location")

@tool
def web_search(query: str, max_results: int = 8, sites: List[str] = None) -> List[Dict[str, Any]]:
    """Enhanced web search with site filtering and fallback mechanisms"""
    try:
        # Updated import for new ddgs package
        from ddgs import DDGS
        
        # Build search query with site filtering
        if sites:
            site_filters = " OR ".join([f"site:{site}" for site in sites])
            search_query = f"({site_filters}) {query}"
        else:
            search_query = query
        
        logger.info(f"Performing web search for: {search_query}")
        
        # Use new DDGS interface
        ddgs = DDGS()
        results = ddgs.text(search_query, max_results=max_results)
        
        if not results:
            logger.warning(f"No results found for query: {search_query}")
            return []
        
        # Format results consistently
        formatted_results = []
        for result in results:
            formatted_result = {
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", ""),
                "source": "ddgs"
            }
            formatted_results.append(formatted_result)
        
        logger.info(f"Found {len(formatted_results)} search results for query: {query}")
        return formatted_results
        
    except ImportError:
        logger.error("DDGS package not available. Install with: pip install ddgs")
        return [{"error": "Search unavailable - missing ddgs package"}]
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

@tool
def singapore_housing_search(query: str, search_type: str = "general", max_results: int = 6) -> str:
    """Singapore-specific housing search with AWS RAG integration and fallbacks"""
    try:
        # Enhanced query mapping for Singapore housing
        enhanced_queries = {
            "general": f"Singapore housing {query}",
            "grants": f"Singapore housing grants eligibility {query} site:cpf.gov.sg OR site:hdb.gov.sg",
            "policies": f"Singapore HDB housing policy regulations {query} site:hdb.gov.sg",
            "market": f"Singapore property market trends {query} site:ura.gov.sg OR site:realis.sg"
        }
        
        enhanced_query = enhanced_queries.get(search_type, f"Singapore housing {query}")
        
        # Try AWS RAG first if available
        if AWS_RAG_AVAILABLE:
            try:
                domain_mapping = {
                    "grants": "grant_schemes",
                    "policies": "hdb_policies", 
                    "market": "market_data"
                }
                domain = domain_mapping.get(search_type, "hdb_policies")
                
                aws_result = singapore_housing_aws_search(query, domain)
                if aws_result and "error" not in str(aws_result).lower():
                    logger.info(f"AWS RAG search successful for: {query}")
                    return aws_result
            except Exception as e:
                logger.warning(f"AWS RAG search failed, falling back to web search: {e}")
        
        # Fallback to web search
        logger.info(f"Using web search fallback for Singapore housing query: {enhanced_query}")
        search_results = web_search(enhanced_query, max_results)
        
        if not search_results or (len(search_results) == 1 and "error" in search_results[0]):
            return "No Singapore housing information found for your query."
        
        # Format results as readable text
        formatted_response = f"**Singapore Housing Search Results for: {query}**\n\n"
        
        for i, result in enumerate(search_results[:max_results], 1):
            if "error" not in result:
                formatted_response += f"{i}. **{result.get('title', 'No title')}**\n"
                formatted_response += f"   {result.get('snippet', 'No description')}\n"
                formatted_response += f"   Source: {result.get('url', 'No URL')}\n\n"
        
        return formatted_response
        
    except Exception as e:
        logger.error(f"Singapore housing search error: {e}")
        return f"Singapore housing search failed: {str(e)}"