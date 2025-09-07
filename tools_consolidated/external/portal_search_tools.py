# tools_consolidated/external/portal_search_tools.py
"""
Portal search tool with caching and multiple search engines.
Based on the original portal_search_tool.py with proper fallback logic.
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

# Environment variables for search engines - FIXED NAMES FROM ORIGINAL
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")

# Price extraction regex
PRICE_RE = re.compile(r'\$[\s]*[\d,]+')

# Thread-safe in-memory cache with TTL and LRU eviction
_cache = OrderedDict()
_cache_lock = threading.Lock()

def _make_cache_key(query: str, sites: List[str], max_results: int) -> str:
    sites_key = ",".join(sorted(sites)) if sites else ""
    return f"q={query}::sites={sites_key}::n={max_results}"

def _cache_get(key: str) -> Optional[List[Dict[str, Any]]]:
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        ts, value = entry
        if (time.time() - ts) > CACHE_TTL:
            # expired
            logger.debug("cache expired for key=%s", key)
            _cache.pop(key, None)
            return None
        # Move to end to mark as recently used (LRU)
        _cache.move_to_end(key, last=True)
        logger.debug("cache hit for key=%s", key)
        return list(value)  # return a shallow copy to prevent caller mutations affecting cache

def _cache_set(key: str, value: List[Dict[str, Any]]):
    with _cache_lock:
        # insert/update
        _cache[key] = (time.time(), list(value))
        _cache.move_to_end(key, last=True)
        # Evict oldest if over capacity
        while len(_cache) > CACHE_MAX_ITEMS:
            popped_key, _ = _cache.popitem(last=False)
            logger.debug("evicted cache key=%s due to cache size limit", popped_key)
        logger.debug("cached key=%s (ttl=%s sec)", key, CACHE_TTL)

def extract_price_from_text(text: str) -> Optional[float]:
    if not text:
        return None
    m = PRICE_RE.search(text)
    if not m:
        return None
    p = m.group(0).replace('$', '').replace(' ', '').replace(',', '')
    try:
        return float(p)
    except Exception:
        return None

def google_cse_search(query: str, num: int = 10) -> List[Dict[str, Any]]:
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        logger.debug("Google CSE not configured; skipping google_cse_search")
        return []
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_API_KEY, "cx": GOOGLE_CX, "q": query, "num": min(10, num)}
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) or []
        results = []
        
        for it in items:
            title = it.get("title")
            link = it.get("link")
            snippet = it.get("snippet") or ""
            price = extract_price_from_text(title) or extract_price_from_text(snippet)
            results.append({
                "title": title,
                "url": link,
                "snippet": snippet,
                "domain": urlparse(link).netloc if link else "",
                "price": price,
                "source": "google_cse"
            })
        return results
    except Exception as e:
        logger.error(f"Google CSE search failed: {e}")
        return []

def ddg_search(query: str, num: int = 8) -> List[Dict[str, Any]]:
    try:
        # Use the ORIGINAL import method from portal_search_tool.py
        from duckduckgo_search import ddg
        hits = ddg(query, region='wt-wt', safesearch='Off', timelimit='y', max_results=num)
        results = []
        for it in hits or []:
            link = it.get("href") or it.get("url")
            title = it.get("title")
            snippet = it.get("body") or it.get("snippet") or ""
            price = extract_price_from_text(title) or extract_price_from_text(snippet)
            results.append({
                "title": title,
                "url": link,
                "snippet": snippet,
                "domain": urlparse(link).netloc if link else "",
                "price": price,
                "source": "ddg"
            })
        return results
    except ImportError:
        logger.error("duckduckgo_search not installed")
        return []
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []

def dedupe_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for r in results:
        u = r.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(r)
    return out

@tool
def search_property_portals(query: str, sites: List[str] = None, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search specified portal domains for the query.
    Returns deduplicated list of {title, url, snippet, domain, price, source}.
    Caching: results stored in an in-memory TTL cache keyed by (query, sites, n).
    """
    if sites is None:
        sites = ["propertyguru.com.sg", "99.co"]
    
    site_query = " OR ".join(f"site:{s}" for s in sites)
    full_query = f"{site_query} {query}"
    cache_key = _make_cache_key(full_query, sites, max_results)

    # 1) Try cache
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug(f"Returning cached results for: {query}")
        return cached[:max_results]

    results = []
    # 2) Primary: Google CSE
    try:
        if GOOGLE_API_KEY and GOOGLE_CX:
            results = google_cse_search(full_query, num=max_results)
            logger.info(f"Google CSE returned {len(results)} results")
        else:
            logger.warning("Google CSE not configured (missing API_KEY or CSE_ID)")
    except Exception as e:
        logger.warning("google_cse_search failed: %s", e)

    # 3) Fallback: DuckDuckGo
    if not results:
        try:
            results = ddg_search(full_query, num=max_results)
            logger.info(f"DuckDuckGo fallback returned {len(results)} results")
        except Exception as e:
            logger.warning("ddg_search failed: %s", e)

    # 4) Deduplicate & sort: prefer items with price info
    deduped = dedupe_results(results)
    deduped.sort(key=lambda x: (0 if x.get("price") is not None else 1, x.get("price") or float('inf')))

    # 5) Cache and return
    _cache_set(cache_key, deduped)
    logger.info(f"Returning {len(deduped)} deduplicated results for: {query}")
    return deduped[:max_results]

@tool
def get_supported_portals() -> List[str]:
    """Get list of supported property portals"""
    return ["propertyguru.com.sg", "99.co", "hdb.gov.sg", "edgeprop.sg"]

@tool
def validate_portal_configuration() -> Dict[str, Any]:
    """Validate portal search configuration and available engines"""
    config_status = {
        'google_cse': {
            'api_key_configured': bool(GOOGLE_API_KEY),
            'search_engine_configured': bool(GOOGLE_CX),
            'available': bool(GOOGLE_API_KEY and GOOGLE_CX)
        },
        'duckduckgo': {'available': False}
    }
    
    # Check DuckDuckGo availability with ORIGINAL import method
    try:
        from duckduckgo_search import ddg
        config_status['duckduckgo']['available'] = True
    except ImportError:
        config_status['duckduckgo']['available'] = False
    
    return {
        'configuration': config_status,
        'supported_portals': get_supported_portals(),
        'available_engines': [
            engine for engine, info in config_status.items() 
            if info.get('available', False)
        ],
        'cache_config': {
            'ttl_seconds': CACHE_TTL,
            'max_items': CACHE_MAX_ITEMS
        }
    }

@tool
def clear_portal_cache():
    """Clear the portal search cache (useful for testing/debugging)"""
    with _cache_lock:
        _cache.clear()
    return "Portal search cache cleared"

# Backward compatibility aliases
search_portals = search_property_portals  # Original function name