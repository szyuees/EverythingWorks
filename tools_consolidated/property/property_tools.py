# tools_consolidated/property/property_tools.py
import logging
from typing import Dict, List, Any, Optional
from strands import tool
from urllib.parse import urlparse
import re

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

def extract_price_from_text(text: str) -> Optional[float]:
    """Extract price from text content"""
    if not text:
        return None
    
    # Look for price patterns like $800,000 or $800k
    price_patterns = [
        r'\$\s*(\d{1,3}(?:,\d{3})*)',  # $800,000
        r'\$\s*(\d+)k',                # $800k
        r'SGD\s*(\d{1,3}(?:,\d{3})*)', # SGD 800,000
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                if 'k' in match.group(0).lower():
                    return float(price_str) * 1000
                else:
                    return float(price_str)
            except ValueError:
                continue
    return None

def validate_property_data(properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and enrich property data with realistic checks"""
    validated_properties = []
    
    for prop in properties:
        try:
            # Basic validation - skip if no URL or title
            if not prop.get('url') or not prop.get('title'):
                continue
            
            # Price validation and extraction
            price = prop.get('price')
            if not price or price == 0:
                # Try to extract price from title or snippet
                price = extract_price_from_text(prop.get('title', '')) or \
                       extract_price_from_text(prop.get('snippet', ''))
            
            if price and isinstance(price, (int, float)) and price > 100000:
                prop['price'] = int(price)
            else:
                prop['price'] = None
                prop['price_note'] = "Price not available - contact agent"
            
            # Room extraction validation
            rooms = prop.get('rooms')
            if not rooms:
                title_lower = prop.get('title', '').lower()
                snippet_lower = prop.get('snippet', '').lower()
                
                for text in [title_lower, snippet_lower]:
                    room_match = re.search(r'(\d+)[-\s]?(?:room|bed)', text)
                    if room_match:
                        rooms = int(room_match.group(1))
                        break
            
            prop['rooms'] = rooms or 'Not specified'
            
            # Location validation
            location = prop.get('location')
            if not location or location == 'Singapore':
                title_text = prop.get('title', '').lower()
                url_text = prop.get('url', '').lower()
                
                sg_areas = [
                    'tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan',
                    'toa payoh', 'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok',
                    'yishun', 'bukit merah', 'queenstown', 'kallang', 'marine parade',
                    'pasir ris', 'choa chu kang', 'bukit panjang', 'sembawang'
                ]
                
                for area in sg_areas:
                    if area in title_text or area in url_text:
                        location = area.title()
                        break
            
            prop['location'] = location or 'Singapore'
            
            # URL validation - check if specific listing or category page
            url = prop.get('url', '')
            is_specific_listing = any(indicator in url.lower() for indicator in [
                '/listing/', '/property/', '/unit/', '/flat/', '/apartment/',
                'id=', 'propertyid', 'listingid'
            ])
            
            if not is_specific_listing:
                prop['url_type'] = 'category_page'
                prop['note'] = 'Category page - multiple listings available'
            else:
                prop['url_type'] = 'specific_listing'
            
            # Add data quality score
            quality_score = 0
            if prop.get('price') and isinstance(prop['price'], int):
                quality_score += 3
            if prop.get('rooms') and prop['rooms'] != 'Not specified':
                quality_score += 2
            if prop.get('location') and prop['location'] != 'Singapore':
                quality_score += 2
            if is_specific_listing:
                quality_score += 3
            
            prop['data_quality_score'] = quality_score
            validated_properties.append(prop)
            
        except Exception as e:
            logger.warning(f"Property validation error: {e}")
            prop['validation_error'] = str(e)
            validated_properties.append(prop)
    
    # Sort by data quality score (highest first)
    validated_properties.sort(key=lambda x: x.get('data_quality_score', 0), reverse=True)
    
    return validated_properties


@tool
def property_search(query: str, max_results: int = 6, sites: List[str] = None) -> List[Dict[str, Any]]:
    """Enhanced property search with validation"""
    try:
        if sites is None:
            sites = ["propertyguru.com.sg", "99.co", "hdb.gov.sg", "edgeprop.sg"]
        
        # Use portal search
        results = search_property_portals(query, sites, max_results)
        
        if not results:
            return [{"error": "No properties found for the given criteria"}]
        
        # Validate and enrich property data
        validated_results = validate_property_data(results)
        
        # Add system note about data limitations
        if validated_results:
            validated_results[0]['system_note'] = (
                "Property data is aggregated from multiple sources. "
                "Prices and availability should be verified directly with listing agents."
            )
        
        return validated_results[:max_results]
        
    except Exception as e:
        logger.error(f"Property search error: {e}")
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
    """
    Scrape detailed property information from Singapore property listing URLs
    with proper error handling and site-specific parsing
    """
    try:
        # Check if beautifulsoup4 is available
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return {
                "error": "Property detail scraping unavailable - missing beautifulsoup4 dependency",
                "url": url,
                "suggestion": "Install beautifulsoup4: pip install beautifulsoup4"
            }
        
        # Basic URL validation
        if not url or not url.startswith(('http://', 'https://')):
            return {"error": "Invalid URL provided", "url": url}
        
        # Import required modules
        import requests
        import time
        from urllib.parse import urlparse
        
        domain = urlparse(url).netloc.lower()
        
        # Rate limiting - respect the websites
        time.sleep(1)
        
        # Make request with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Initialize result structure
        property_details = {
            "url": url,
            "source_domain": domain,
            "scraping_timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "success": True
        }
        
        # Site-specific parsing logic
        if 'propertyguru.com.sg' in domain:
            property_details.update(_parse_propertyguru(soup))
        elif '99.co' in domain:
            property_details.update(_parse_99co(soup))
        elif 'hdb.gov.sg' in domain:
            property_details.update(_parse_hdb(soup))
        elif 'edgeprop.sg' in domain:
            property_details.update(_parse_edgeprop(soup))
        else:
            # Generic parsing for unknown sites
            property_details.update(_parse_generic(soup))
            property_details["note"] = f"Generic parsing used for {domain}"
        
        # Apply validation to scraped data
        validated_details = validate_property_data([property_details])
        
        if validated_details:
            result = validated_details[0]
            result["scraping_method"] = "detailed_scrape"
            return result
        else:
            return {
                "error": "Property details could not be validated",
                "url": url,
                "raw_data_available": bool(property_details)
            }
        
    except requests.exceptions.Timeout:
        return {
            "error": "Request timeout - website took too long to respond",
            "url": url,
            "suggestion": "Try again later or check if URL is accessible"
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Network error: {str(e)}",
            "url": url,
            "suggestion": "Check internet connection and URL validity"
        }
    except Exception as e:
        logger.error(f"Property scraping error for {url}: {e}")
        return {
            "error": f"Scraping failed: {str(e)}",
            "url": url,
            "suggestion": "URL may not be a valid property listing"
        }

def _parse_propertyguru(soup) -> Dict[str, Any]:
    """Parse PropertyGuru specific elements"""
    details = {}
    
    try:
        # Title
        title_elem = soup.find('h1', class_='property-title') or soup.find('h1')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
        
        # Price
        price_elem = soup.find('span', class_='price') or soup.find(class_='property-price')
        if price_elem:
            price_text = price_elem.get_text().strip()
            details['price_text'] = price_text
            # Extract numeric price
            price_num = extract_price_from_text(price_text)
            if price_num:
                details['price'] = price_num
        
        # Property details
        details_section = soup.find('div', class_='property-details') or soup.find('div', class_='listing-details')
        if details_section:
            # Extract bedrooms, bathrooms, size, etc.
            for item in details_section.find_all(['span', 'div']):
                text = item.get_text().strip().lower()
                if 'bed' in text:
                    beds_match = re.search(r'(\d+)', text)
                    if beds_match:
                        details['bedrooms'] = int(beds_match.group(1))
                elif 'bath' in text:
                    baths_match = re.search(r'(\d+)', text)
                    if baths_match:
                        details['bathrooms'] = int(baths_match.group(1))
                elif 'sqft' in text or 'sq ft' in text:
                    size_match = re.search(r'(\d+(?:,\d+)?)', text.replace(',', ''))
                    if size_match:
                        details['size_sqft'] = int(size_match.group(1).replace(',', ''))
        
        # Location
        location_elem = soup.find('span', class_='location') or soup.find(class_='property-location')
        if location_elem:
            details['location'] = location_elem.get_text().strip()
            
    except Exception as e:
        details['parsing_error'] = f"PropertyGuru parsing error: {str(e)}"
    
    return details

def _parse_99co(soup) -> Dict[str, Any]:
    """Parse 99.co specific elements"""
    details = {}
    
    try:
        # Title
        title_elem = soup.find('h1') or soup.find(class_='listing-title')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
        
        # Price - 99.co specific selectors
        price_elem = soup.find(class_='price-display') or soup.find(class_='listing-price')
        if price_elem:
            price_text = price_elem.get_text().strip()
            details['price_text'] = price_text
            price_num = extract_price_from_text(price_text)
            if price_num:
                details['price'] = price_num
        
        # Property attributes
        attrs = soup.find_all(class_='attribute-item') or soup.find_all(class_='property-attribute')
        for attr in attrs:
            text = attr.get_text().strip().lower()
            if 'bedroom' in text:
                beds_match = re.search(r'(\d+)', text)
                if beds_match:
                    details['bedrooms'] = int(beds_match.group(1))
            elif 'bathroom' in text:
                baths_match = re.search(r'(\d+)', text)
                if baths_match:
                    details['bathrooms'] = int(baths_match.group(1))
    
    except Exception as e:
        details['parsing_error'] = f"99.co parsing error: {str(e)}"
    
    return details

def _parse_hdb(soup) -> Dict[str, Any]:
    """Parse HDB.gov.sg specific elements"""
    details = {}
    
    try:
        # HDB resale listings have specific structure
        details['property_type'] = 'HDB'
        
        # Look for flat type
        flat_type_elem = soup.find(text=re.compile(r'\d+\s*room', re.I))
        if flat_type_elem:
            details['flat_type'] = flat_type_elem.strip()
            
        # Look for price in HDB format
        price_elems = soup.find_all(text=re.compile(r'\$[\d,]+'))
        for price_text in price_elems:
            price_num = extract_price_from_text(price_text)
            if price_num and price_num > 100000:  # Reasonable HDB price
                details['price'] = price_num
                details['price_text'] = price_text.strip()
                break
                
    except Exception as e:
        details['parsing_error'] = f"HDB parsing error: {str(e)}"
    
    return details

def _parse_edgeprop(soup) -> Dict[str, Any]:
    """Parse EdgeProp specific elements"""
    details = {}
    
    try:
        # Similar to PropertyGuru but with EdgeProp specific classes
        title_elem = soup.find('h1') or soup.find(class_='property-name')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
            
        # EdgeProp price format
        price_elem = soup.find(class_='price') or soup.find(class_='property-price-value')
        if price_elem:
            price_text = price_elem.get_text().strip()
            details['price_text'] = price_text
            price_num = extract_price_from_text(price_text)
            if price_num:
                details['price'] = price_num
                
    except Exception as e:
        details['parsing_error'] = f"EdgeProp parsing error: {str(e)}"
    
    return details

def _parse_generic(soup) -> Dict[str, Any]:
    """Generic parsing for unknown property sites"""
    details = {}
    
    try:
        # Try to find title
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            details['title'] = title_elem.get_text().strip()
        
        # Look for price patterns in the entire page
        page_text = soup.get_text()
        price_num = extract_price_from_text(page_text)
        if price_num:
            details['price'] = price_num
        
        # Try to find property type
        text_lower = page_text.lower()
        if 'hdb' in text_lower:
            details['property_type'] = 'HDB'
        elif 'condo' in text_lower or 'condominium' in text_lower:
            details['property_type'] = 'Private'
        elif 'executive' in text_lower and 'condo' in text_lower:
            details['property_type'] = 'EC'
            
        details['parsing_method'] = 'generic'
        
    except Exception as e:
        details['parsing_error'] = f"Generic parsing error: {str(e)}"
    
    return details

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