# tools_consolidated/property/property_tools.py
import logging
import time
from typing import Dict, List, Any, Optional
from strands import tool
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Import portal search and HTTP tools
try:
    from portal_search_tool import search_portals
    PORTAL_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("Portal search tool not available")
    PORTAL_SEARCH_AVAILABLE = False

try:
    from tools_consolidated.http.http_tools import enhanced_http_request, validate_urls
    HTTP_TOOLS_AVAILABLE = True
except ImportError:
    # Fallback during transition
    try:
        from enhanced_http_tools import enhanced_http_request, validate_property_urls as validate_urls
        HTTP_TOOLS_AVAILABLE = True
    except ImportError:
        logger.warning("HTTP tools not available")
        HTTP_TOOLS_AVAILABLE = False

@tool
def property_search(query: str, max_results: int = 6, sites: List[str] = None) -> List[Dict[str, Any]]:
    """
    Search property portals and return validated listing URLs.
    Primary method uses portal search with Google CSE, fallback to DuckDuckGo.
    """
    try:
        if sites is None:
            sites = ["propertyguru.com.sg", "99.co"]

        if not PORTAL_SEARCH_AVAILABLE:
            logger.warning("Portal search not available, using fallback")
            return _fallback_property_search(query, max_results, sites)

        # Use portal search (Google CSE primary, DDG fallback)
        search_results = search_portals(query, sites=sites, max_results=max_results)

        # Convert to standardized listing format
        listings = []
        for result in search_results:
            listing = {
                "name": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("url", ""),
                "domain": result.get("domain", ""),
                "price": result.get("price", 0),
                "source": result.get("source", ""),
                "rooms": _extract_rooms_from_title(result.get("title", "")),
                "location": _extract_location_from_title(result.get("title", "")),
                "ranking_reason": f"Found via {result.get('source', 'search')}"
            }
            listings.append(listing)

        # Validate URLs if HTTP tools available
        if HTTP_TOOLS_AVAILABLE and validate_urls:
            validated_listings = validate_urls(listings)
            return validated_listings if validated_listings else listings

        return listings

    except Exception as e:
        logger.error(f"Property search failed: {e}")
        return {"error": str(e)}

def _fallback_property_search(query: str, max_results: int, sites: List[str]) -> List[Dict[str, Any]]:
    """Fallback property search using direct web search"""
    try:
        from tools_consolidated.search.search_tools import web_search
        
        all_results = []
        for site in sites:
            site_results = web_search(query, max_results=max_results//len(sites), site_filter=site)
            for result in site_results:
                listing = {
                    "name": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("url", ""),
                    "domain": result.get("domain", ""),
                    "price": 0,  # Would need scraping to get actual price
                    "source": "web_search_fallback",
                    "rooms": _extract_rooms_from_title(result.get("title", "")),
                    "location": _extract_location_from_title(result.get("title", "")),
                    "ranking_reason": "Fallback search result"
                }
                all_results.append(listing)
        
        return all_results
        
    except Exception as e:
        logger.error(f"Fallback property search failed: {e}")
        return []

@tool
def filter_and_rank_properties(results: List[Dict[str, Any]], location: str = None, 
                              max_price: float = None, flat_type: str = None, k: int = 3) -> List[Dict[str, Any]]:
    """Enhanced property filtering and ranking with multiple criteria"""
    try:
        if not isinstance(results, list) or not results:
            return []
        
        filtered_results = results.copy()
        
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
            if listing.get('url_validated', False):
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
            
            return score
        
        # Sort by ranking score
        filtered_results.sort(key=calculate_ranking_score, reverse=True)
        
        return filtered_results[:k]
        
    except Exception as e:
        logger.error(f"Filter and rank error: {e}")
        return []

def _extract_rooms_from_title(title: str) -> int:
    """Extract number of rooms from property title"""
    import re
    try:
        rooms_match = re.search(r'(\d+)[-\s]?(room|bed)', title.lower())
        return int(rooms_match.group(1)) if rooms_match else 0
    except:
        return 0

def _extract_location_from_title(title: str) -> str:
    """Extract Singapore location from title"""
    singapore_areas = [
        'tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan', 
        'toa payoh', 'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok',
        'yishun', 'choa chu kang', 'pasir ris', 'sembawang', 'kallang', 'geylang'
    ]
    
    title_lower = title.lower()
    for area in singapore_areas:
        if area in title_lower:
            return area.title()
    
    return "Singapore"

@tool
def scrape_property_details(url: str) -> Dict[str, Any]:
    """Scrape additional property details from a listing URL"""
    try:
        if not HTTP_TOOLS_AVAILABLE:
            return {"error": "HTTP tools not available"}
        
        response_data = enhanced_http_request(url)
        if not response_data.get('success'):
            return {"error": "Failed to fetch property page"}
        
        html_content = response_data.get('content', '')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract additional details
        details = {
            'url': url,
            'title': soup.find('h1').get_text().strip() if soup.find('h1') else '',
            'description': _extract_description(soup),
            'amenities': _extract_amenities(soup),
            'floor_info': _extract_floor_info(soup),
            'area_info': _extract_area_info(soup)
        }
        
        return details
        
    except Exception as e:
        logger.error(f"Property scraping error for {url}: {e}")
        return {"error": str(e)}

def _extract_description(soup: BeautifulSoup) -> str:
    """Extract property description from page"""
    # Look for common description selectors
    selectors = ['.description', '.property-description', '.listing-description', 'p']
    
    for selector in selectors:
        elements = soup.select(selector)
        for element in elements:
            text = element.get_text().strip()
            if len(text) > 50:  # Meaningful description
                return text[:500]  # Limit length
    
    return ""

def _extract_amenities(soup: BeautifulSoup) -> List[str]:
    """Extract nearby amenities from property page"""
    amenities = []
    amenity_keywords = ['mrt', 'bus', 'school', 'mall', 'park', 'clinic', 'market', 'gym']
    
    text_content = soup.get_text().lower()
    for keyword in amenity_keywords:
        if keyword in text_content:
            amenities.append(keyword.upper())
    
    return list(set(amenities))  # Remove duplicates

def _extract_floor_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract floor information from property page"""
    import re
    try:
        text_content = soup.get_text()
        floor_match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*floor', text_content.lower())
        
        return {
            'floor_level': int(floor_match.group(1)) if floor_match else None,
            'floor_info_available': floor_match is not None
        }
    except:
        return {'floor_level': None, 'floor_info_available': False}

def _extract_area_info(soup: BeautifulSoup) -> Dict[str, Any]:
    """Extract area/size information from property page"""
    import re
    try:
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