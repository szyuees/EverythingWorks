# tools_consolidated/external/portal_search_tools.py
"""
Consolidated portal search functionality with caching and multiple search engines.
Integrates the best features from the original portal_search_tool.py
"""

import os
import re
import time
import logging
import threading
import requests
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional
from collections import OrderedDict
from strands import tool
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Environment-configurable cache parameters
CACHE_TTL = int(os.getenv("PORTAL_SEARCH_CACHE_TTL", "60"))       # seconds
CACHE_MAX_ITEMS = int(os.getenv("PORTAL_SEARCH_CACHE_MAX", "200"))  # maximum cache keys

# Environment variables for search engines
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX") or os.getenv("GOOGLE_CSE_ID")

# Price extraction regex
PRICE_RE = re.compile(r'\$[\s]*[\d,]+')

# Thread-safe in-memory cache with TTL and LRU eviction
_cache = OrderedDict()
_cache_lock = threading.Lock()

class PortalSearchManager:
    """Enhanced portal search manager with caching and multiple engines"""
    
    def __init__(self):
        self.supported_sites = [
            "propertyguru.com.sg",
            "99.co", 
            "hdb.gov.sg",
            "edgeprop.sg"
        ]
    
    def search_portals(self, query: str, sites: List[str] = None, 
                      max_results: int = 8) -> List[Dict[str, Any]]:
        """
        Search property portals with caching and multiple search engines.
        Primary: Google CSE, Fallback: DuckDuckGo
        """
        if sites is None:
            sites = self.supported_sites
        
        # Build site query
        site_query = " OR ".join(f"site:{s}" for s in sites)
        full_query = f"{site_query} {query}"
        
        # Check cache first
        cache_key = self._make_cache_key(full_query, sites, max_results)
        cached_results = self._cache_get(cache_key)
        if cached_results is not None:
            logger.debug(f"Cache hit for query: {query}")
            return cached_results[:max_results]
        
        results = []
        
        # Try Google CSE first
        try:
            results = self._google_cse_search(full_query, num=max_results)
            if results:
                logger.info(f"Google CSE returned {len(results)} results for: {query}")
        except Exception as e:
            logger.warning(f"Google CSE search failed: {e}")
        
        # Fallback to DuckDuckGo if insufficient results
        if len(results) < max_results:
            remaining = max_results - len(results)
            try:
                ddg_results = self._duckduckgo_search(full_query, num=remaining)
                if ddg_results:
                    results.extend(ddg_results)
                    logger.info(f"DuckDuckGo provided {len(ddg_results)} additional results")
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")
        
        # Process and enhance results
        processed_results = []
        for result in results:
            processed = self._process_search_result(result)
            if processed:
                processed_results.append(processed)
        
        # Deduplicate and sort by price availability
        final_results = self._dedupe_and_sort(processed_results)
        
        # Cache the results
        self._cache_set(cache_key, final_results)
        
        return final_results[:max_results]
    
    def _google_cse_search(self, query: str, num: int = 10) -> List[Dict[str, Any]]:
        """Google Custom Search Engine implementation"""
        if not GOOGLE_API_KEY or not GOOGLE_CX:
            logger.debug("Google CSE not configured")
            return []
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "num": min(10, num)  # Google CSE max is 10
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            items = data.get("items", []) or []
            
            for item in items:
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                
                # Extract price information
                price = self._extract_price(title) or self._extract_price(snippet)
                
                result = {
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "domain": urlparse(link).netloc if link else "",
                    "price": price,
                    "source": "google_cse"
                }
                results.append(result)
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"Google CSE request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Google CSE processing error: {e}")
            return []
    
    def _duckduckgo_search(self, query: str, num: int = 8) -> List[Dict[str, Any]]:
        """DuckDuckGo search implementation"""
        try:
            from duckduckgo_search import DDGS
            
            ddgs = DDGS()
            search_results = ddgs.text(query, max_results=num)
            
            results = []
            for item in search_results or []:
                title = item.get("title", "")
                link = item.get("href", "") or item.get("url", "")
                snippet = item.get("body", "") or item.get("snippet", "")
                
                # Extract price information
                price = self._extract_price(title) or self._extract_price(snippet)
                
                result = {
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "domain": urlparse(link).netloc if link else "",
                    "price": price,
                    "source": "duckduckgo"
                }
                results.append(result)
            
            return results
            
        except ImportError:
            logger.error("duckduckgo-search package not installed")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price from text using multiple patterns"""
        if not text:
            return# tools_consolidated/external/portal_search_tools.py
"""
Consolidated portal search functionality for property searches.
This replaces the standalone portal_search_tool.py
"""

import logging
import re
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import requests
from strands import tool

logger = logging.getLogger(__name__)

class PortalSearchManager:
    """Manages search across different property portals"""
    
    def __init__(self):
        self.supported_sites = [
            "propertyguru.com.sg",
            "99.co", 
            "hdb.gov.sg",
            "edgeprop.sg"
        ]
        self.search_engines = {
            'google_cse': self._google_cse_search,
            'duckduckgo': self._duckduckgo_search
        }
    
    def search_portals(self, query: str, sites: List[str] = None, 
                      max_results: int = 6) -> List[Dict[str, Any]]:
        """
        Search property portals using available search engines.
        Primary: Google CSE, Fallback: DuckDuckGo
        """
        if sites is None:
            sites = self.supported_sites
        
        results = []
        
        # Try Google CSE first
        try:
            google_results = self._google_cse_search(query, sites, max_results)
            if google_results:
                results.extend(google_results)
                logger.info(f"Google CSE returned {len(google_results)} results")
        except Exception as e:
            logger.warning(f"Google CSE search failed: {e}")
        
        # If insufficient results, try DuckDuckGo
        if len(results) < max_results:
            remaining = max_results - len(results)
            try:
                ddg_results = self._duckduckgo_search(query, sites, remaining)
                if ddg_results:
                    results.extend(ddg_results)
                    logger.info(f"DuckDuckGo returned {len(ddg_results)} additional results")
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed: {e}")
        
        # Process and enhance results
        processed_results = []
        for result in results[:max_results]:
            processed = self._process_search_result(result)
            if processed:
                processed_results.append(processed)
        
        return processed_results
    
    def _google_cse_search(self, query: str, sites: List[str], 
                          max_results: int) -> List[Dict[str, Any]]:
        """Google Custom Search Engine implementation"""
        
        # Check for Google CSE configuration
        import os
        api_key = os.getenv('GOOGLE_CSE_API_KEY')
        search_engine_id = os.getenv('GOOGLE_CSE_ID')
        
        if not api_key or not search_engine_id:
            logger.warning("Google CSE not configured (missing API_KEY or CSE_ID)")
            return []
        
        results = []
        
        for site in sites:
            try:
                site_query = f"{query} site:{site}"
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': api_key,
                    'cx': search_engine_id,
                    'q': site_query,
                    'num': min(10, max_results)  # Google CSE max is 10
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('items', [])
                for item in items:
                    result = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'domain': urlparse(item.get('link', '')).netloc,
                        'source': 'google_cse'
                    }
                    results.append(result)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Google CSE search error for {site}: {e}")
                continue
        
        return results
    
    def _duckduckgo_search(self, query: str, sites: List[str], 
                          max_results: int) -> List[Dict[str, Any]]:
        """DuckDuckGo search implementation"""
        
        try:
            from duckduckgo_search import DDGS
            
            results = []
            per_site = max(1, max_results // len(sites))
            
            for site in sites:
                try:
                    site_query = f"{query} site:{site}"
                    ddgs = DDGS()
                    search_results = ddgs.text(site_query, max_results=per_site)
                    
                    for item in search_results:
                        result = {
                            'title': item.get('title', ''),
                            'url': item.get('href', ''),
                            'snippet': item.get('body', ''),
                            'domain': urlparse(item.get('href', '')).netloc,
                            'source': 'duckduckgo'
                        }
                        results.append(result)
                    
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"DuckDuckGo search error for {site}: {e}")
                    continue
            
            return results
            
        except ImportError:
            logger.error("duckduckgo-search not available")
            return []
    
    def _process_search_result(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process and enhance search results"""
        try:
            # Extract price from title/snippet
            price = self._extract_price(result.get('title', '') + ' ' + result.get('snippet', ''))
            
            # Validate URL
            url = result.get('url', '')
            if not url or not self._is_valid_property_url(url):
                return None
            
            processed = {
                'title': result.get('title', '').strip(),
                'url': url,
                'snippet': result.get('snippet', '').strip(),
                'domain': result.get('domain', ''),
                'source': result.get('source', 'unknown'),
                'price': price,
                'rooms': self._extract_rooms(result.get('title', '')),
                'location': self._extract_location(result.get('title', ''))
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing search result: {e}")
            return None
    
    def _extract_price(self, text: str) -> int:
        """Extract price from text"""
        try:
            # Look for various price patterns
            patterns = [
                r'\$\s*([\d,]+)',  # $500,000
                r'SGD\s*([\d,]+)', # SGD 500,000
                r'S\$\s*([\d,]+)', # S$ 500,000
                r'([\d,]+)\s*k',   # 500k
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(',', '')
                    price = int(price_str)
                    
                    # Handle 'k' notation
                    if 'k' in match.group(0).lower():
                        price *= 1000
                    
                    # Reasonable price range for Singapore
                    if 100000 <= price <= 5000000:
                        return price
            
            return 0
            
        except Exception:
            return 0
    
    def _extract_rooms(self, text: str) -> int:
        """Extract number of rooms from text"""
        try:
            room_match = re.search(r'(\d+)[-\s]?(room|bed)', text.lower())
            return int(room_match.group(1)) if room_match else 0
        except:
            return 0
    
    def _extract_location(self, text: str) -> str:
        """Extract Singapore location from text"""
        singapore_areas = [
            'tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan',
            'toa payoh', 'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok',
            'yishun', 'choa chu kang', 'pasir ris', 'sembawang', 'kallang', 'geylang',
            'bukit timah', 'orchard', 'marina bay', 'sentosa'
        ]
        
        text_lower = text.lower()
        for area in singapore_areas:
            if area in text_lower:
                return area.title()
        
        return "Singapore"
    
    def _is_valid_property_url(self, url: str) -> bool:
        """Check if URL is a valid property listing URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check if it's from supported sites
            if not any(site in domain for site in self.supported_sites):
                return False
            
            # Check URL structure (basic validation)
            path = parsed.path.lower()
            if any(keyword in path for keyword in ['listing', 'property', 'sale', 'rent', 'hdb']):
                return True
            
            return True  # Allow other URLs from supported domains
            
        except Exception:
            return False

# Global portal search manager
portal_manager = PortalSearchManager()

@tool
def search_property_portals(query: str, sites: List[str] = None, 
                           max_results: int = 6) -> List[Dict[str, Any]]:
    """
    Search property portals for listings.
    
    Args:
        query: Search query (e.g., "3 room HDB Tampines")
        sites: List of sites to search (defaults to major SG property sites)
        max_results: Maximum number of results to return
    
    Returns:
        List of property listings with metadata
    """
    try:
        return portal_manager.search_portals(query, sites, max_results)
    except Exception as e:
        logger.error(f"Portal search failed: {e}")
        return []

@tool
def get_supported_portals() -> List[str]:
    """Get list of supported property portals"""
    return portal_manager.supported_sites

@tool
def validate_portal_configuration() -> Dict[str, Any]:
    """Validate portal search configuration"""
    import os
    
    config_status = {
        'google_cse': {
            'api_key': bool(os.getenv('GOOGLE_CSE_API_KEY')),
            'search_engine_id': bool(os.getenv('GOOGLE_CSE_ID'))
        },
        'duckduckgo': True  # Always available if package is installed
    }
    
    try:
        from duckduckgo_search import DDGS
        config_status['duckduckgo'] = True
    except ImportError:
        config_status['duckduckgo'] = False
    
    return {
        'configuration': config_status,
        'supported_portals': portal_manager.supported_sites,
        'available_engines': [
            engine for engine, available in [
                ('google_cse', config_status['google_cse']['api_key'] and config_status['google_cse']['search_engine_id']),
                ('duckduckgo', config_status['duckduckgo'])
            ] if available
        ]
    }

# Backward compatibility - alias for existing usage
search_portals = search_property_portals