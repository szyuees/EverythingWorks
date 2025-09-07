# tools_consolidated/__init__.py
"""
Consolidated tools package for the Singapore Housing AI Assistant.

This package provides organized, efficient tools for:
- Search operations (web search, Singapore-specific housing search)
- Property operations (search, filtering, validation)  
- Financial calculations (affordability, loans, CPF)
- HTTP operations (requests, validation, metadata extraction)
- AWS RAG operations (knowledge base search)

All tools are managed through a central registry for dependency tracking
and availability checking.
"""

# Import registry first
from .registry import tool_registry, get_available_tools, get_tool_status

# Import individual tool categories
from .search import web_search, singapore_housing_search
from .property import property_search, filter_and_rank_properties, scrape_property_details  
from .financial import (
    calculate_affordability, calculate_loan_repayment,
    calculate_repayment_duration, calculate_cpf_utilization
)
from .http import enhanced_http_request, validate_urls, extract_property_metadata

# Try to import AWS tools (optional)
try:
    from ragtool.aws_rag_tools import aws_rag_search, singapore_housing_aws_search
    AWS_TOOLS_AVAILABLE = True
except ImportError:
    AWS_TOOLS_AVAILABLE = False

# Export all available tools
__all__ = [
    # Registry
    'tool_registry', 'get_available_tools', 'get_tool_status',
    
    # Search tools
    'web_search', 'singapore_housing_search',
    
    # Property tools
    'property_search', 'filter_and_rank_properties', 'scrape_property_details',
    
    # Financial tools
    'calculate_affordability', 'calculate_loan_repayment',
    'calculate_repayment_duration', 'calculate_cpf_utilization',
    
    # HTTP tools
    'enhanced_http_request', 'validate_urls', 'extract_property_metadata'
]

# Add AWS tools to exports if available
if AWS_TOOLS_AVAILABLE:
    __all__.extend(['aws_rag_search', 'singapore_housing_aws_search'])

# Version and metadata
__version__ = "1.0.0"
__description__ = "Consolidated tools for Singapore Housing AI Assistant"