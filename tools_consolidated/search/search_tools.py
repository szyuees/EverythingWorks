# tools_consolidated/search/search_tools.py
import logging
from typing import Dict, List, Any, Optional
from strands import tool
from duckduckgo_search import DDGS
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Check AWS RAG availability
try:
    from ragtool.aws_rag_tools import singapore_housing_aws_search
    AWS_RAG_AVAILABLE = True
except ImportError:
    AWS_RAG_AVAILABLE = False
    singapore_housing_aws_search = None

@tool
def web_search(query: str, max_results: int = 5, site_filter: str = None) -> List[Dict[str, Any]]:
    """Enhanced web search using DuckDuckGo with better error handling and filtering"""
    try:
        # Add site filter if specified
        if site_filter:
            query = f"{query} site:{site_filter}"
        
        results = []
        ddgs = DDGS()
        search_results = ddgs.text(query, max_results=max_results)
        
        for item in search_results:
            result = {
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", ""),
                "domain": urlparse(item.get("href", "")).netloc
            }
            results.append(result)
            
        logger.info(f"Found {len(results)} search results for query: {query}")
        return results if results else []
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return []

@tool
def singapore_housing_search(query: str, search_type: str = "general", max_results: int = 5) -> List[Dict[str, Any]]:
    """Enhanced Singapore-specific housing search with AWS RAG integration"""
    
    # Try AWS RAG first if available
    if AWS_RAG_AVAILABLE and singapore_housing_aws_search:
        try:
            if search_type in ["grants", "policies"]:
                domain = "grant_schemes" if search_type == "grants" else "hdb_policies"
                rag_result = singapore_housing_aws_search(query, domain)
                if rag_result and "error" not in str(rag_result).lower():
                    return [{"source": "AWS_RAG", "content": rag_result, "type": "knowledge_base"}]
        except Exception as e:
            logger.warning(f"AWS RAG search failed: {e}")
    
    # Fallback to web search with Singapore context
    singapore_query = f"{query} Singapore"
    
    # Add search type specific terms and site filters
    site_filter = None
    if search_type == "grants":
        singapore_query += " HDB grants CPF housing scheme"
        site_filter = "hdb.gov.sg"
    elif search_type == "policies": 
        singapore_query += " HDB policy eligibility"
        site_filter = "hdb.gov.sg"
    elif search_type == "properties":
        # For properties, delegate to property search tools
        return []
    
    results = web_search(singapore_query, max_results, site_filter)
    
    # Prioritize official sources
    official_domains = ['hdb.gov.sg', 'cpf.gov.sg', 'gov.sg', 'ura.gov.sg']
    prioritized = []
    regular = []
    
    for result in results:
        url = result.get('url', '').lower()
        if any(domain in url for domain in official_domains):
            result['priority'] = 'official'
            prioritized.append(result)
        else:
            result['priority'] = 'general'
            regular.append(result)
    
    return prioritized + regular