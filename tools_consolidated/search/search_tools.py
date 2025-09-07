# tools_consolidated/search/search_tools.py
import logging
from typing import Dict, List, Any, Optional
from strands import tool
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Check AWS RAG availability - SAFE IMPORT ORDER
AWS_RAG_AVAILABLE = False
aws_singapore_search = None

# Only try consolidated location since this is a new repo
try:
    from tools_consolidated.aws.aws_tools import singapore_housing_aws_search as aws_singapore_search
    AWS_RAG_AVAILABLE = True
    logger.info("AWS RAG tools loaded from consolidated location")
except ImportError:
    logger.info("AWS RAG tools not available - will use web search only")
    AWS_RAG_AVAILABLE = False

# Check DuckDuckGo availability
DUCKDUCKGO_AVAILABLE = False
try:
    from duckduckgo_search import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    logger.warning("DuckDuckGo search not available - install duckduckgo-search package")

@tool
def web_search(query: str, max_results: int = 5, site_filter: str = None) -> List[Dict[str, Any]]:
    """Enhanced web search using DuckDuckGo with better error handling and filtering"""
    try:
        if not DUCKDUCKGO_AVAILABLE:
            return [{"error": "DuckDuckGo search not available - missing dependency 'duckduckgo-search'"}]
        
        # Add site filter if specified
        search_query = f"{query} site:{site_filter}" if site_filter else query
        
        results = []
        ddgs = DDGS()
        search_results = ddgs.text(search_query, max_results=max_results)
        
        for item in search_results or []:
            result = {
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "url": item.get("href", ""),
                "domain": urlparse(item.get("href", "")).netloc if item.get("href") else "",
                "source": "duckduckgo"
            }
            results.append(result)
            
        logger.info(f"Found {len(results)} search results for query: {query}")
        return results if results else []
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return [{"error": f"Search failed: {str(e)}"}]

@tool
def singapore_housing_search(query: str, search_type: str = "general", max_results: int = 5) -> List[Dict[str, Any]]:
    """Enhanced Singapore-specific housing search with AWS RAG integration"""
    
    # Try AWS RAG first for relevant search types
    if AWS_RAG_AVAILABLE and aws_singapore_search and search_type in ["grants", "policies"]:
        try:
            domain = "grant_schemes" if search_type == "grants" else "hdb_policies"
            rag_result = aws_singapore_search(query, domain)
            
            # Check if RAG result is valid and useful
            if rag_result and isinstance(rag_result, str) and len(rag_result.strip()) > 0:
                if "error" not in str(rag_result).lower():
                    return [{
                        "source": "AWS_RAG", 
                        "content": rag_result, 
                        "type": "knowledge_base",
                        "title": f"Singapore Housing {search_type.title()} Information",
                        "url": "aws://knowledge-base",
                        "snippet": rag_result[:200] + "..." if len(rag_result) > 200 else rag_result
                    }]
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
        # For properties, suggest using property search tools instead
        return [{
            "title": "Property Search Recommendation",
            "snippet": "For property listings, please use the property search tools for better results",
            "url": "",
            "domain": "",
            "source": "system_recommendation",
            "recommendation": "Use property_search tool for property listings"
        }]
    
    results = web_search(singapore_query, max_results, site_filter)
    
    # Enhance results with priority marking for official sources
    if results and isinstance(results, list):
        official_domains = ['hdb.gov.sg', 'cpf.gov.sg', 'gov.sg', 'ura.gov.sg']
        for result in results:
            if isinstance(result, dict) and not result.get('error'):
                url = result.get('url', '').lower()
                if any(domain in url for domain in official_domains):
                    result['priority'] = 'official'
                    result['source_type'] = 'government'
                else:
                    result['priority'] = 'general'
                    result['source_type'] = 'web'
        
        # Sort by priority (official sources first)
        try:
            results.sort(key=lambda x: 0 if x.get('priority') == 'official' else 1)
        except (AttributeError, TypeError):
            pass  # Skip sorting if results have inconsistent structure
    
    return results

@tool
def validate_search_configuration() -> Dict[str, Any]:
    """Validate search tool configuration and dependencies"""
    config = {
        'duckduckgo_available': DUCKDUCKGO_AVAILABLE,
        'aws_rag_available': AWS_RAG_AVAILABLE,
        'supported_search_types': ['general', 'grants', 'policies', 'properties'],
        'official_domains': ['hdb.gov.sg', 'cpf.gov.sg', 'gov.sg', 'ura.gov.sg'],
        'recommendations': []
    }
    
    if not DUCKDUCKGO_AVAILABLE:
        config['duckduckgo_error'] = "Install duckduckgo-search package: pip install duckduckgo-search"
        config['recommendations'].append("Install duckduckgo-search for web search functionality")
    
    if not AWS_RAG_AVAILABLE:
        config['aws_rag_error'] = "AWS RAG tools not configured - check AWS credentials and tools_consolidated.aws module"
        config['recommendations'].append("Configure AWS credentials and tools for enhanced knowledge base search")
    
    return config