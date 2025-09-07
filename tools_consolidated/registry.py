# tools_consolidated/registry.py
"""
Central tool registry for managing all available tools and their dependencies.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolInfo:
    """Information about a tool and its availability"""
    name: str
    function: Callable
    category: str
    description: str
    dependencies: List[str]
    available: bool = True
    error_message: Optional[str] = None

class ToolRegistry:
    """Central registry for managing all tools"""
    
    def __init__(self):
        self.tools: Dict[str, ToolInfo] = {}
        self.categories: Dict[str, List[str]] = {}
        self.initialize_tools()
    
    def initialize_tools(self):
        """Initialize all available tools with dependency checking"""
        logger.info("Initializing tool registry...")
        
        # Search tools
        self._register_search_tools()
        
        # Property tools  
        self._register_property_tools()
        
        # Financial tools
        self._register_financial_tools()
        
        # HTTP tools
        self._register_http_tools()
        
        # AWS RAG tools (optional)
        self._register_aws_tools()
        
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
                dependencies=["duckduckgo_search"]
            )
            
            self.register_tool(
                name="singapore_housing_search",
                function=singapore_housing_search,
                category="search", 
                description="Singapore-specific housing search with AWS RAG integration",
                dependencies=["duckduckgo_search"]
            )
            
        except ImportError as e:
            logger.error(f"Failed to register search tools: {e}")
    
    def _register_property_tools(self):
        """Register property-related tools"""
        try:
            from tools_consolidated.property import (
                property_search, filter_and_rank_properties, scrape_property_details
            )
            
            self.register_tool(
                name="property_search",
                function=property_search,
                category="property",
                description="Search property listings from official Singapore portals",
                dependencies=["portal_search_tool", "duckduckgo_search"]
            )
            
            self.register_tool(
                name="filter_and_rank_properties", 
                function=filter_and_rank_properties,
                category="property",
                description="Filter and rank property listings by criteria",
                dependencies=[]
            )
            
            self.register_tool(
                name="scrape_property_details",
                function=scrape_property_details,
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
        """Register HTTP and web-related tools"""
        try:
            from tools_consolidated.http import (
                enhanced_http_request, validate_urls, extract_property_metadata
            )
            
            self.register_tool(
                name="enhanced_http_request",
                function=enhanced_http_request,
                category="http",
                description="Make HTTP requests with session management",
                dependencies=["requests", "beautifulsoup4"]
            )
            
            self.register_tool(
                name="validate_urls",
                function=validate_urls,
                category="http",
                description="Validate URL accessibility and extract metadata",
                dependencies=["requests", "beautifulsoup4"]
            )
            
            self.register_tool(
                name="extract_property_metadata",
                function=extract_property_metadata,
                category="http",
                description="Extract property metadata from HTML content",
                dependencies=["beautifulsoup4"]
            )
            
        except ImportError as e:
            logger.error(f"Failed to register HTTP tools: {e}")
    
    def _register_aws_tools(self):
        """Register AWS RAG tools (optional)"""
        try:
            from ragtool.aws_rag_tools import (
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
    
    def register_tool(self, name: str, function: Callable, category: str, 
                     description: str, dependencies: List[str]):
        """Register a tool with dependency checking"""
        
        # Check dependencies
        available = True
        error_message = None
        
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                available = False
                error_message = f"Missing dependency: {dep}"
                break
        
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
        
        if not available:
            logger.warning(f"Tool '{name}' registered but unavailable: {error_message}")
    
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
        return [tool.function for tool in available_tools]
    
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
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get detailed status report of all tools"""
        report = {
            "total_tools": len(self.tools),
            "available_tools": sum(1 for tool in self.tools.values() if tool.available),
            "categories": {}
        }
        
        for category, tool_names in self.categories.items():
            available_tools = []
            unavailable_tools = []
            
            for name in tool_names:
                tool = self.tools[name]
                if tool.available:
                    available_tools.append({
                        "name": name,
                        "description": tool.description
                    })
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