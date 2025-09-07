# tools_consolidated/property/property_tools.py
import logging
from typing import Dict, List, Any, Optional
from strands import tool
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Import BeautifulSoup with fallback
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    logger.warning("BeautifulSoup4 not available - scraping functionality limited")
    BeautifulSoup = None
    BS4_AVAILABLE = False

# SAFE PORTAL SEARCH IMPORT
PORTAL_SEARCH_AVAILABLE = False
search_property_portals = None

try:
    from tools_consolidated.external.portal_search_tools import search_property_portals
    PORTAL_SEARCH_AVAILABLE = True
    logger.info("Portal search tools loaded successfully")
except ImportError:
    logger.info("Portal search tools not available - will use fallback")

# SAFE HTTP TOOLS IMPORT
HTTP_TOOLS_AVAILABLE = False
enhanced_http_request = validate_urls = None

try:
    from tools_consolidated.http.http_tools import enhanced_http_request, validate_urls
    HTTP_TOOLS_AVAILABLE = True
    logger.info("HTTP tools loaded successfully")
except ImportError:
    logger.info("HTTP tools not available - URL validation disabled")

@tool
def property_search(query: str, max_results: int = 6, sites: List[str] = None) -> List[Dict[str, Any]]:
    """
    Search property portals and return validated listing URLs.
    Primary method uses portal search with Google CSE, fallback to DuckDuckGo.
    """
    try:
        if sites is None:
            sites = ["propertyguru.com.sg", "99.co"]

        # Check if portal search is available
        if not PORTAL_SEARCH_AVAILABLE or search_property_portals is None:
            logger.info("Portal search not available, using web search fallback")
            return _fallback_property_search(query, max_results, sites)

        # Use portal search
        search_results = search_property_portals(query, sites=sites, max_results=max_results)

        # Handle empty or error results
        if not search_results or not isinstance(search_results, list):
            logger.warning("Portal search returned no results, using fallback")
            return _fallback_property_search(query, max_results, sites)

        # Convert to standardized listing format
        listings = []
        for result in search_results:
            if isinstance(result, dict):
                listing = {
                    "name": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("url", ""),
                    "domain": result.get("domain", ""),
                    "price": result.get("price", 0),
                    "source": result.get("source", "portal_search"),
                    "rooms": _extract_rooms_from_title(result.get("title", "")),
                    "location": _extract_location_from_title(result.get("title", "")),
                    "ranking_reason": f"Found via {result.get('source', 'search')}"
                }
                listings.append(listing)

        # Validate URLs if HTTP tools available
        if HTTP_TOOLS_AVAILABLE and validate_urls and listings:
            try:
                validated_listings = validate_urls(listings)
                return validated_listings if validated_listings else listings
            except Exception as e:
                logger.warning(f"URL validation failed: {e}")
                return listings

        return listings if listings else _fallback_property_search(query, max_results, sites)

    except Exception as e:
        logger.error(f"Property search failed: {e}")
        return [{"error": f"Property search failed: {str(e)}"}]

def _fallback_property_search(query: str, max_results: int, sites: List[str]) -> List[Dict[str, Any]]:
    """Fallback property search using DuckDuckGo - FIXED TO MATCH ORIGINAL"""
    try:
        # Use the SAME DuckDuckGo import as the original portal_search_tool.py
        try:
            from duckduckgo_search import ddg
            logger.info("Using DuckDuckGo fallback search")
            
            all_results = []
            per_site = max(1, max_results // len(sites))
            
            for site in sites:
                try:
                    site_query = f"{query} site:{site}"
                    hits = ddg(site_query, region='wt-wt', safesearch='Off', timelimit='y', max_results=per_site)
                    
                    for item in hits or []:
                        listing = {
                            "name": item.get("title", ""),
                            "snippet": item.get("body", "") or item.get("snippet", ""),
                            "url": item.get("href", "") or item.get("url", ""),
                            "domain": site,
                            "price": 0,  # Would need scraping to get actual price
                            "source": "ddg_fallback",
                            "rooms": _extract_rooms_from_title(item.get("title", "")),
                            "location": _extract_location_from_title(item.get("title", "")),
                            "ranking_reason": "DuckDuckGo fallback search result"
                        }
                        all_results.append(listing)
                        
                except Exception as e:
                    logger.warning(f"DuckDuckGo search failed for {site}: {e}")
                    continue
            
            return all_results if all_results else [{"error": "DuckDuckGo fallback search failed"}]
            
        except ImportError:
            logger.error("duckduckgo-search not available for fallback")
            return [{"error": "No search tools available - install duckduckgo-search package"}]
        
    except Exception as e:
        logger.error(f"Fallback property search failed: {e}")
        return [{"error": f"All property search methods failed: {str(e)}"}]

@tool
def filter_and_rank_properties(results: List[Dict[str, Any]], location: str = None, 
                              max_price: float = None, flat_type: str = None, k: int = 3) -> List[Dict[str, Any]]:
    """Enhanced property filtering and ranking with multiple criteria"""
    try:
        if not isinstance(results, list) or not results:
            return []
        
        # Filter out error results
        valid_results = [r for r in results if isinstance(r, dict) and not r.get('error')]
        if not valid_results:
            return []
        
        filtered_results = valid_results.copy()
        
        # Location filtering
        if location:
            location_lower = location.lower()
            filtered_results = [
                r for r in filtered_results 
                if (
                    location_lower in r.get('location', '').lower() or
                    location_lower in r.get('name', '').lower() or
                    location_lower in r.get('snippet', '').lower()
                )
            ]
        
        # Price filtering
        if max_price:
            try:
                max_price_num = float(str(max_price).replace(',', '').replace('$', ''))
                filtered_results = [
                    r for r in filtered_results
                    if r.get('price', 0) <= max_price_num or r.get('price', 0) == 0
                ]
            except (ValueError, TypeError):
                logger.warning(f"Invalid max_price format: {max_price}")
        
        # Flat type filtering
        if flat_type:
            flat_type_lower = flat_type.lower()
            filtered_results = [
                r for r in filtered_results
                if (
                    flat_type_lower in r.get('name', '').lower() or
                    str(r.get('rooms', 0)) in flat_type_lower
                )
            ]
        
        # Enhanced ranking
        def calculate_ranking_score(listing):
            score = 0
            
            # URL validation bonus
            if listing.get('url_validated'):
                score += 3
            
            # Official site bonus
            url = listing.get('url', '')
            official_sites = ['propertyguru.com.sg', '99.co', 'hdb.gov.sg']
            if any(site in url for site in official_sites):
                score += 2
            
            # Complete information bonuses
            if listing.get('price', 0) > 0:
                score += 2
            if listing.get('location') and listing.get('rooms'):
                score += 1
            if listing.get('snippet'):
                score += 1
            
            # Source quality bonus
            source = listing.get('source', '')
            if 'google_cse' in source:
                score += 2
            elif 'portal_search' in source:
                score += 1
            
            return score
        
        # Sort by ranking score
        try:
            filtered_results.sort(key=calculate_ranking_score, reverse=True)
        except Exception as e:
            logger.warning(f"Ranking failed: {e}")
        
        return filtered_results[:k]
        
    except Exception as e:
        logger.error(f"Filter and rank error: {e}")
        return results[:k] if isinstance(results, list) else []

@tool
def scrape_property_details(url: str) -> Dict[str, Any]:
    """Scrape additional property details from a listing URL"""
    try:
        if not HTTP_TOOLS_AVAILABLE or enhanced_http_request is None:
            return {"error": "HTTP tools not available for scraping"}
        
        if not BS4_AVAILABLE:
            return {"error": "BeautifulSoup4 not available - install with: pip install beautifulsoup4"}
        
        response_data = enhanced_http_request(url)
        if not isinstance(response_data, dict) or not response_data.get('success'):
            return {"error": "Failed to fetch property page"}
        
        html_content = response_data.get('content', '')
        if not html_content:
            return {"error": "No content received from URL"}
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract additional details
        details = {
            'url': url,
            'title': _safe_extract_text(soup.find('h1')) if soup.find('h1') else '',
            'description': _extract_description(soup),
            'amenities': _extract_amenities(soup),
            'floor_info': _extract_floor_info(soup),
            'area_info': _extract_area_info(soup)
        }
        
        return details
        
    except Exception as e:
        logger.error(f"Property scraping error for {url}: {e}")
        return {"error": str(e)}

def _extract_rooms_from_title(title: str) -> int:
    """Extract number of rooms from property title"""
    import re
    try:
        if not title:
            return 0
        rooms_match = re.search(r'(\d+)[-\s]?(room|bed)', title.lower())
        return int(rooms_match.group(1)) if rooms_match else 0
    except:
        return 0

def _extract_location_from_title(title: str) -> str:
    """Extract Singapore location from title"""
    if not title:
        return "Singapore"
        
    singapore_areas = [
        'tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan',
        'toa payoh', 'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok',
        'yishun', 'choa chu kang', 'pasir ris', 'sembawang', 'kallang', 'geylang',
        'bukit timah', 'orchard', 'marina bay', 'sentosa'
    ]
    
    title_lower = title.lower()
    for area in singapore_areas:
        if area in title_lower:
            return area.title()
    
    return "Singapore"

def _safe_extract_text(element) -> str:
    """Safely extract text from BeautifulSoup element"""
    try:
        return element.get_text().strip() if element else ''
    except:
        return ''

def _extract_description(soup) -> str:
    """Extract property description from page"""
    if not soup:
        return ""
        
    selectors = ['.description', '.property-description', '.listing-description', 'p']
    
    for selector in selectors:
        try:
            elements = soup.select(selector)
            for element in elements:
                text = _safe_extract_text(element)
                if len(text) > 50:  # Meaningful description
                    return text[:500]  # Limit length
        except:
            continue
    
    return ""

def _extract_amenities(soup) -> List[str]:
    """Extract nearby amenities from property page"""
    if not soup:
        return []
        
    amenities = []
    amenity_keywords = ['mrt', 'bus', 'school', 'mall', 'park', 'clinic', 'market', 'gym']
    
    try:
        text_content = soup.get_text().lower()
        for keyword in amenity_keywords:
            if keyword in text_content:
                amenities.append(keyword.upper())
    except:
        pass
    
    return list(set(amenities))  # Remove duplicates

def _extract_floor_info(soup) -> Dict[str, Any]:
    """Extract floor information from property page"""
    import re
    try:
        if not soup:
            return {'floor_level': None, 'floor_info_available': False}
            
        text_content = soup.get_text()
        floor_match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*floor', text_content.lower())
        
        return {
            'floor_level': int(floor_match.group(1)) if floor_match else None,
            'floor_info_available': floor_match is not None
        }
    except:
        return {'floor_level': None, 'floor_info_available': False}

def _extract_area_info(soup) -> Dict[str, Any]:
    """Extract area/size information from property page"""
    import re
    try:
        if not soup:
            return {'area_info_available': False}
            
        text_content = soup.get_text()
        # Look for sqft, sqm patterns
        area_match = re.search(r'(\d+(?:,\d{3})*)\s*(sqft|sq ft|sqm|sq m)', text_content.lower())
        
        if area_match:
            size = int(area_match.group(1).replace(',', ''))
            unit = area_match.group(2)
            return {
                'size': size,
                'unit': unit,
                'area_info_available': True
            }
        
        return {'area_info_available': False}
    except:
        return {'area_info_available': False}