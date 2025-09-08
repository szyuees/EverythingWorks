# tools_consolidated/registry.py - Environment-aware registry with robust fallbacks
"""
Central tool registry for managing all available tools and their dependencies.
Handles environment mismatches and missing dependencies gracefully.
"""

import logging
import sys
import importlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolInfo:
    """Information about a tool and its availability"""
    name: str
    function: Optional[Callable]
    category: str
    description: str
    dependencies: List[str]
    available: bool = True
    error_message: Optional[str] = None

class ToolRegistry:
    """Central registry for managing all tools with environment awareness"""
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self.categories: Dict[str, List[str]] = {}
        self.environment_info = self._get_environment_info()
        self.initialize_tools()
    
    def _get_environment_info(self) -> Dict[str, Any]:
        """Get current Python environment information"""
        info = {
            'python_executable': sys.executable,
            'python_version': sys.version,
            'environment_type': 'conda' if 'conda' in sys.executable.lower() else 'system'
        }
        logger.info(f"Python environment: {info['environment_type']} - {info['python_executable']}")
        return info
    
    def _check_dependency_robust(self, dependency: str) -> tuple[bool, str]:
        """Robustly check if a dependency is available with detailed error info"""
        try:
            # Handle common import name variations
            import_names = {
                'beautifulsoup4': ['bs4', 'BeautifulSoup4'],
                'duckduckgo-search': ['duckduckgo_search'],
                'python-dotenv': ['dotenv']
            }
            
            names_to_try = import_names.get(dependency, [dependency.replace('-', '_')])
            
            for name in names_to_try:
                try:
                    module = importlib.import_module(name)
                    # Additional verification for beautifulsoup4
                    if dependency == 'beautifulsoup4':
                        from bs4 import BeautifulSoup  # Test actual functionality
                    return True, f"Available as {name}"
                except ImportError:
                    continue
            
            return False, f"Not found (tried: {', '.join(names_to_try)})"
            
        except Exception as e:
            return False, f"Import error: {str(e)}"
    
    def initialize_tools(self):
        """Initialize all available tools with dependency checking"""
        logger.info("Initializing tool registry with environment awareness...")
        
        # Search tools
        self._register_search_tools()
        
        # Property tools  
        self._register_property_tools()
        
        # Financial tools
        self._register_financial_tools()
        
        # HTTP tools with fallbacks
        self._register_http_tools()
        
        # AWS RAG tools
        self._register_aws_tools()
        
        # External service tools
        self._register_external_tools()
        
        logger.info(f"Tool registry initialized with {len(self.tools)} tools")
        self._log_tool_status()
    
    def _register_search_tools(self):
        """Register search-related tools"""
        try:
            from tools_consolidated.search import web_search, singapore_housing_search
            
            self.register_tool(
                name="web_search",
                function=web_search,
                category="search",
                description="Enhanced web search with site filtering",
                dependencies=["duckduckgo-search"]
            )
            
            self.register_tool(
                name="singapore_housing_search",
                function=singapore_housing_search,
                category="search", 
                description="Singapore-specific housing search with AWS RAG integration",
                dependencies=["duckduckgo-search"]
            )
            
        except ImportError as e:
            logger.error(f"Failed to register search tools: {e}")
    
    def _register_property_tools(self):
        """Register property-related tools"""
        try:
            from tools_consolidated.property import property_search, filter_and_rank_properties
            
            self.register_tool(
                name="property_search",
                function=property_search,
                category="property",
                description="Search property listings from official Singapore portals",
                dependencies=["duckduckgo-search", "requests"]
            )
            
            self.register_tool(
                name="filter_and_rank_properties", 
                function=filter_and_rank_properties,
                category="property",
                description="Filter and rank property listings by criteria",
                dependencies=[]
            )
            
            # Conditional registration for scrape_property_details
            bs4_available, bs4_status = self._check_dependency_robust("beautifulsoup4")
            
            if bs4_available:
                try:
                    from tools_consolidated.property import scrape_property_details
                    scrape_function = scrape_property_details
                except ImportError:
                    scrape_function = self._create_scrape_fallback()
            else:
                scrape_function = self._create_scrape_fallback()
            
            self.register_tool(
                name="scrape_property_details",
                function=scrape_function,
                category="property",
                description="Extract detailed information from property listing pages",
                dependencies=["beautifulsoup4", "requests"]
            )
            
        except ImportError as e:
            logger.error(f"Failed to register property tools: {e}")
    
    def _register_financial_tools(self):
        """Register financial calculation tools"""
        try:
            from tools_consolidated.financial import (
                calculate_affordability, calculate_loan_repayment,
                calculate_repayment_duration, calculate_cpf_utilization
            )
            
            self.register_tool(
                name="calculate_affordability",
                function=calculate_affordability,
                category="financial",
                description="Calculate housing affordability with Singapore guidelines",
                dependencies=[]
            )
            
            self.register_tool(
                name="calculate_loan_repayment",
                function=calculate_loan_repayment,
                category="financial", 
                description="Calculate detailed loan repayment schedules",
                dependencies=[]
            )
            
            self.register_tool(
                name="calculate_repayment_duration",
                function=calculate_repayment_duration,
                category="financial",
                description="Calculate loan repayment duration",
                dependencies=[]
            )
            
            self.register_tool(
                name="calculate_cpf_utilization",
                function=calculate_cpf_utilization,
                category="financial",
                description="Calculate CPF usage for property purchase",
                dependencies=[]
            )
            
        except ImportError as e:
            logger.error(f"Failed to register financial tools: {e}")
    
    def _register_http_tools(self):
        """Register HTTP and web-related tools with smart fallbacks"""
        
        # Check if beautifulsoup4 is actually available
        bs4_available, bs4_status = self._check_dependency_robust("beautifulsoup4")
        logger.info(f"BeautifulSoup4 status: {bs4_status}")
        
        # Create appropriate functions based on availability
        if bs4_available:
            try:
                from tools_consolidated.http import (
                    enhanced_http_request, validate_urls, extract_property_metadata
                )
                http_func = enhanced_http_request
                validate_func = validate_urls
                metadata_func = extract_property_metadata
                logger.info("Using full HTTP tools with BeautifulSoup4")
            except ImportError as e:
                logger.warning(f"Failed to import HTTP tools despite BS4 availability: {e}")
                http_func = self._create_http_fallback()
                validate_func = self._create_url_validation_fallback()
                metadata_func = self._create_metadata_fallback()
        else:
            logger.info("Using fallback HTTP tools (BeautifulSoup4 not available)")
            http_func = self._create_http_fallback()
            validate_func = self._create_url_validation_fallback()
            metadata_func = self._create_metadata_fallback()
        
        self.register_tool(
            name="enhanced_http_request",
            function=http_func,
            category="http",
            description="Make HTTP requests with session management",
            dependencies=["requests", "beautifulsoup4"]
        )
        
        self.register_tool(
            name="validate_urls",
            function=validate_func,
            category="http",
            description="Validate URL accessibility and extract metadata",
            dependencies=["requests", "beautifulsoup4"]
        )
        
        self.register_tool(
            name="extract_property_metadata",
            function=metadata_func,
            category="http",
            description="Extract property metadata from HTML content",
            dependencies=["beautifulsoup4"]
        )
    
    def _register_aws_tools(self):
        """Register AWS RAG tools"""
        try:
            from tools_consolidated.aws import (
                aws_rag_search, singapore_housing_aws_search, 
                validate_aws_rag_configuration
            )
            
            self.register_tool(
                name="aws_rag_search",
                function=aws_rag_search,
                category="aws",
                description="Search AWS Knowledge Base",
                dependencies=["boto3"]
            )
            
            self.register_tool(
                name="singapore_housing_aws_search",
                function=singapore_housing_aws_search,
                category="aws",
                description="Singapore-specific AWS Knowledge Base search",
                dependencies=["boto3"]
            )
            
            self.register_tool(
                name="validate_aws_rag_configuration",
                function=validate_aws_rag_configuration,
                category="aws",
                description="Validate AWS RAG system configuration",
                dependencies=["boto3"]
            )
            
            logger.info("AWS RAG tools registered successfully")
            
        except ImportError as e:
            logger.warning(f"AWS RAG tools not available: {e}")
        except Exception as e:
            logger.error(f"Failed to register AWS tools: {e}")
    
    def _register_external_tools(self):
        """Register external service integration tools"""
        try:
            from tools_consolidated.external import (
                search_property_portals, get_supported_portals,
                validate_portal_configuration
            )
            
            self.register_tool(
                name="search_property_portals",
                function=search_property_portals,
                category="external",
                description="Search property portals using Google CSE and DuckDuckGo",
                dependencies=["duckduckgo-search", "requests"]
            )
            
            self.register_tool(
                name="get_supported_portals",
                function=get_supported_portals,
                category="external",
                description="Get list of supported property portals",
                dependencies=[]
            )
            
            self.register_tool(
                name="validate_portal_configuration", 
                function=validate_portal_configuration,
                category="external",
                description="Validate external portal search configuration",
                dependencies=["requests"]
            )
            
            logger.info("External service tools registered successfully")
            
        except ImportError as e:
            logger.warning(f"External service tools not available: {e}")
        except Exception as e:
            logger.error(f"Failed to register external tools: {e}")
    
    def register_tool(self, name: str, function: Callable, category: str, 
                     description: str, dependencies: List[str]):
        """Register a tool with robust dependency checking"""
        
        # Check dependencies with detailed reporting
        available = True
        error_messages = []
        
        for dep in dependencies:
            dep_available, dep_status = self._check_dependency_robust(dep)
            if not dep_available:
                available = False
                error_messages.append(f"{dep}: {dep_status}")
        
        error_message = "; ".join(error_messages) if error_messages else None
        
        # Only log warnings for critical tools
        if not available and name in ['enhanced_http_request', 'validate_urls', 'scrape_property_details', 'extract_property_metadata']:
            # Check if we're using a fallback function
            is_fallback = hasattr(function, '__name__') and 'fallback' in function.__name__
            if not is_fallback:
                logger.warning(f"Tool '{name}' registered but unavailable: {error_message}")
        
        # Create tool info
        tool_info = ToolInfo(
            name=name,
            function=function,
            category=category,
            description=description,
            dependencies=dependencies,
            available=available,
            error_message=error_message
        )
        
        # Register tool
        self.tools[name] = tool_info
        
        # Add to category
        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(name)
    
    def _create_scrape_fallback(self):
        """Create fallback function for property scraping"""
        def scrape_fallback(url: str):
            try:
                import requests
                response = requests.get(url, timeout=10)
                return {
                    "url": url,
                    "title": "Title extraction unavailable",
                    "content_preview": response.text[:500],
                    "status_code": response.status_code,
                    "fallback_used": True,
                    "note": "Basic scraping only - install beautifulsoup4 for full property detail extraction"
                }
            except Exception as e:
                return {
                    "error": f"Scraping failed: {str(e)}",
                    "url": url,
                    "fallback_used": True,
                    "suggestion": "Check URL accessibility and install beautifulsoup4"
                }
        return scrape_fallback
    
    def _create_http_fallback(self):
        """Create fallback function for HTTP requests"""
        def http_fallback(url: str, method: str = 'GET', headers: dict = None, **kwargs):
            try:
                import requests
                response = requests.request(method, url, headers=headers, timeout=15, **kwargs)
                return {
                    'status_code': response.status_code,
                    'url': str(response.url),
                    'content': response.text[:2000],  # Limited content
                    'headers': dict(response.headers),
                    'success': True,
                    'fallback_used': True,
                    'note': 'Basic HTTP client - install beautifulsoup4 for enhanced parsing'
                }
            except Exception as e:
                return {
                    'status_code': 0,
                    'url': url,
                    'content': f"Error: {str(e)}",
                    'success': False,
                    'fallback_used': True
                }
        return http_fallback
    
    def _create_url_validation_fallback(self):
        """Create fallback function for URL validation"""
        def url_validation_fallback(listings):
            try:
                import requests
                validated = []
                for listing in listings:
                    if isinstance(listing, dict):
                        url = listing.get('url')
                        if url:
                            try:
                                response = requests.head(url, timeout=5)
                                listing['url_validated'] = response.status_code == 200
                                listing['status_code'] = response.status_code
                            except:
                                listing['url_validated'] = False
                                listing['status_code'] = 0
                        else:
                            listing['url_validated'] = False
                        
                        listing['fallback_used'] = True
                        listing['validation_note'] = 'Basic validation - install beautifulsoup4 for metadata extraction'
                    validated.append(listing)
                return validated
            except Exception as e:
                return listings  # Return as-is if validation fails
        return url_validation_fallback
    
    def _create_metadata_fallback(self):
        """Create fallback function for metadata extraction"""
        def metadata_fallback(html_content: str, url: str):
            import re
            # Basic text-based extraction
            metadata = {'url': url, 'fallback_used': True}
            
            if html_content:
                # Extract title from HTML title tag
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
                if title_match:
                    metadata['title'] = title_match.group(1).strip()
                
                # Look for price patterns
                price_patterns = [r'\$[\d,]+', r'SGD\s*[\d,]+']
                for pattern in price_patterns:
                    price_match = re.search(pattern, html_content)
                    if price_match:
                        metadata['price_text'] = price_match.group(0)
                        break
                
                metadata['note'] = 'Basic text extraction - install beautifulsoup4 for full HTML parsing'
            
            return metadata
        return metadata_fallback
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get tool information by name"""
        return self.tools.get(name)
    
    def get_available_tools(self, category: str = None) -> List[ToolInfo]:
        """Get list of available tools, optionally filtered by category"""
        if category:
            tool_names = self.categories.get(category, [])
            return [self.tools[name] for name in tool_names if self.tools[name].available]
        else:
            return [tool for tool in self.tools.values() if tool.available]
    
    def get_tool_functions(self, category: str = None) -> List[Callable]:
        """Get list of available tool functions for use with agents"""
        available_tools = self.get_available_tools(category)
        return [tool.function for tool in available_tools if tool.function]
    
    def get_tool_names(self, category: str = None) -> List[str]:
        """Get list of available tool names"""
        available_tools = self.get_available_tools(category)
        return [tool.name for tool in available_tools]
    
    def _log_tool_status(self):
        """Log the status of all registered tools"""
        available_count = sum(1 for tool in self.tools.values() if tool.available)
        total_count = len(self.tools)
        
        logger.info(f"Tool Status: {available_count}/{total_count} available")
        
        for category, tool_names in self.categories.items():
            available_in_category = sum(
                1 for name in tool_names if self.tools[name].available
            )
            logger.info(f"  {category}: {available_in_category}/{len(tool_names)} available")
        
        # Log environment info
        logger.info(f"Environment: {self.environment_info['environment_type']}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get detailed status report of all tools"""
        report = {
            "total_tools": len(self.tools),
            "available_tools": sum(1 for tool in self.tools.values() if tool.available),
            "environment": self.environment_info,
            "categories": {}
        }
        
        for category, tool_names in self.categories.items():
            available_tools = []
            unavailable_tools = []
            
            for name in tool_names:
                tool = self.tools[name]
                tool_info = {
                    "name": name,
                    "description": tool.description
                }
                
                if tool.available:
                    # Check if using fallback
                    if hasattr(tool.function, '__name__') and 'fallback' in tool.function.__name__:
                        tool_info["status"] = "fallback"
                    else:
                        tool_info["status"] = "full"
                    available_tools.append(tool_info)
                else:
                    unavailable_tools.append({
                        "name": name,
                        "error": tool.error_message,
                        "dependencies": tool.dependencies
                    })
            
            report["categories"][category] = {
                "available": available_tools,
                "unavailable": unavailable_tools
            }
        
        return report

# Global tool registry instance
tool_registry = ToolRegistry()

# Convenience functions for backward compatibility
def get_available_tools(category: str = None) -> List[Callable]:
    """Get available tool functions"""
    return tool_registry.get_tool_functions(category)

def get_tool_status() -> Dict[str, Any]:
    """Get tool status report"""
    return tool_registry.get_status_report()