# tools_consolidated/http/http_tools.py
import os
import time
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup
from strands import tool
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

class HTTPClient:
    """Centralized HTTP client with session management and anti-bot measures"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
        self.rate_limits = {}  # Track rate limits per domain
        
    def setup_session(self):
        """Configure session with realistic browser headers and retry logic"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def respect_rate_limit(self, domain: str, delay: float = 2.0):
        """Implement rate limiting per domain"""
        current_time = time.time()
        if domain in self.rate_limits:
            time_since_last = current_time - self.rate_limits[domain]
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                logger.info(f"Rate limiting {domain}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.rate_limits[domain] = time.time()
    
    def make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """Make HTTP request with rate limiting and error handling"""
        domain = urlparse(url).netloc
        self.respect_rate_limit(domain)
        
        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise

# Global HTTP client instance
http_client = HTTPClient()

@tool
def enhanced_http_request(url: str, method: str = 'GET', headers: Dict = None, 
                         data: str = None, convert_to_markdown: bool = False) -> Dict[str, Any]:
    """Enhanced HTTP request with session management and content processing"""
    try:
        # Merge custom headers with session headers
        if headers:
            request_headers = {**http_client.session.headers, **headers}
        else:
            request_headers = http_client.session.headers
        
        # Prepare request kwargs
        kwargs = {'headers': request_headers}
        if data:
            kwargs['data'] = data
        
        response = http_client.make_request(url, method, **kwargs)
        
        # Process content
        content = response.text
        if convert_to_markdown and 'text/html' in response.headers.get('content-type', '').lower():
            content = html_to_markdown(content)
        
        return {
            'status_code': response.status_code,
            'url': str(response.url),
            'content': content[:5000],  # Limit content for context
            'headers': dict(response.headers),
            'success': True
        }
        
    except Exception as e:
        logger.error(f"HTTP request error for {url}: {e}")
        return {
            'status_code': 0,
            'url': url,
            'content': f"Error: {str(e)}",
            'headers': {},
            'success': False
        }

@tool
def validate_urls(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate that URLs are accessible and enrich with metadata"""
    validated_listings = []

    for listing in listings:
        url = listing.get('url') or listing.get('link') or listing.get('href')
        if not url:
            listing['url_validated'] = False
            listing['blocked_reason'] = 'no_url'
            validated_listings.append(listing)
            continue

        # robots.txt check
        if not is_allowed_by_robots(url):
            listing['url_validated'] = False
            listing['blocked_reason'] = 'robots_disallow'
            validated_listings.append(listing)
            continue

        try:
            # Try HEAD request first (fast)
            head_resp = http_client.session.head(url, allow_redirects=True, timeout=6)
            
            if head_resp.status_code != 200:
                listing['url_validated'] = False
                listing['blocked_reason'] = f'head_status_{head_resp.status_code}'
                validated_listings.append(listing)
                continue

            # HEAD OK - perform lightweight GET
            resp = enhanced_http_request(url)
            if resp.get('success') and resp.get('status_code') == 200:
                listing['url_validated'] = True
                
                # Try to parse structured data
                metadata = parse_json_ld(resp.get('content', '') or '')
                if metadata:
                    listing['metadata'] = metadata
                    
                validated_listings.append(listing)
            else:
                listing['url_validated'] = False
                listing['blocked_reason'] = f"get_failed_{resp.get('status_code', 'unknown')}"
                validated_listings.append(listing)

        except Exception as e:
            listing['url_validated'] = False
            listing['blocked_reason'] = f"exception:{str(e)}"
            validated_listings.append(listing)

    return validated_listings

def is_allowed_by_robots(url: str, user_agent: str = '*') -> bool:
    """Check if robots.txt allows fetching the URL"""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        # Default to allow if robots.txt cannot be read
        return True

def parse_json_ld(html_content: str) -> Optional[Dict[str, Any]]:
    """Extract JSON-LD structured data from HTML"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                text = script.string or script.get_text()
                obj = json.loads(text)
                
                # Handle list or object
                if isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, dict) and ('price' in item or 'address' in item):
                            return item
                elif isinstance(obj, dict):
                    if 'price' in obj or 'address' in obj or '@type' in obj:
                        return obj
            except json.JSONDecodeError:
                continue
                
    except Exception as e:
        logger.warning(f"JSON-LD parsing error: {e}")
        
    return None

def html_to_markdown(html_content: str) -> str:
    """Convert HTML to markdown format"""
    try:
        import markdownify
        return markdownify.markdownify(html_content, heading_style="ATX")
    except ImportError:
        # Fallback: simple text extraction
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.get_text()

def extract_property_metadata(html_content: str, url: str) -> Dict[str, Any]:
    """Extract property-specific metadata from HTML content"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {'url': url}
        
        # Extract title
        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            metadata['title'] = title_elem.get_text().strip()
        
        # Extract price using various patterns
        price_patterns = [
            r'\$[\d,]+',
            r'SGD\s*[\d,]+',
            r'S\$[\d,]+'
        ]
        
        text_content = soup.get_text()
        for pattern in price_patterns:
            price_match = re.search(pattern, text_content)
            if price_match:
                price_str = re.sub(r'[^\d]', '', price_match.group())
                try:
                    metadata['extracted_price'] = int(price_str)
                    break
                except ValueError:
                    continue
        
        # Extract room information
        room_match = re.search(r'(\d+)[-\s]?(room|bed)', metadata.get('title', '').lower())
        if room_match:
            metadata['extracted_rooms'] = int(room_match.group(1))
        
        # Extract location information
        singapore_areas = [
            'tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan',
            'toa payoh', 'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok'
        ]
        
        title_lower = metadata.get('title', '').lower()
        for area in singapore_areas:
            if area in title_lower:
                metadata['extracted_location'] = area.title()
                break
        
        return metadata
        
    except Exception as e:
        logger.error(f"Metadata extraction error for {url}: {e}")
        return {'url': url, 'error': str(e)}

# Utility functions for backward compatibility
def safe_extract_text(content, max_length=1000):
    """Safely extract text content with length limits"""
    try:
        if not content:
            return ""
        
        text = str(content)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
        
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return f"Error extracting text: {str(e)}"