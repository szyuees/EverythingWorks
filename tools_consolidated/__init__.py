# tools_consolidated/__init__.py
"""
Consolidated tools package for the Singapore Housing AI Assistant.

This package provides organized, efficient tools for:
- Search operations (web search, Singapore-specific housing search)
- Property operations (search, filtering, validation)  
- Financial calculations (affordability, loans, CPF)
- HTTP operations (requests, validation, metadata extraction)
- AWS RAG operations (knowledge base search)
- External services (portal search, APIs)

All tools are managed through a central registry for dependency tracking
and availability checking.
"""

import logging

logger = logging.getLogger(__name__)

# Import registry first
try:
    from .registry import tool_registry, get_available_tools, get_tool_status
    REGISTRY_AVAILABLE = True
except ImportError as e:
    logger.error(f"Tool registry not available: {e}")
    REGISTRY_AVAILABLE = False
    tool_registry = None
    get_available_tools = lambda: []
    get_tool_status = lambda: {"error": "Registry not available"}

# Import individual tool categories
try:
    from .search import web_search, singapore_housing_search
    SEARCH_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Search tools not available: {e}")
    SEARCH_TOOLS_AVAILABLE = False
    web_search = singapore_housing_search = None

try:
    from .property import property_search, filter_and_rank_properties, scrape_property_details
    PROPERTY_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Property tools not available: {e}")
    PROPERTY_TOOLS_AVAILABLE = False
    property_search = filter_and_rank_properties = scrape_property_details = None

try:
    from .financial import (
        calculate_affordability, calculate_loan_repayment,
        calculate_repayment_duration, calculate_cpf_utilization
    )
    FINANCIAL_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Financial tools not available: {e}")
    FINANCIAL_TOOLS_AVAILABLE = False
    calculate_affordability = calculate_loan_repayment = None
    calculate_repayment_duration = calculate_cpf_utilization = None

try:
    from .http import enhanced_http_request, validate_urls, extract_property_metadata
    HTTP_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"HTTP tools not available: {e}")
    HTTP_TOOLS_AVAILABLE = False
    enhanced_http_request = validate_urls = extract_property_metadata = None

# Import AWS tools (now properly consolidated)
try:
    from .aws import aws_rag_search, singapore_housing_aws_search, validate_aws_rag_configuration
    AWS_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AWS tools not available: {e}")
    AWS_TOOLS_AVAILABLE = False
    aws_rag_search = singapore_housing_aws_search = validate_aws_rag_configuration = None

# Import external service tools
try:
    from .external import search_property_portals, get_supported_portals, validate_portal_configuration
    EXTERNAL_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"External service tools not available: {e}")
    EXTERNAL_TOOLS_AVAILABLE = False
    search_property_portals = get_supported_portals = validate_portal_configuration = None

# Build exports list dynamically
__all__ = []

# Registry
if REGISTRY_AVAILABLE:
    __all__.extend(['tool_registry', 'get_available_tools', 'get_tool_status'])

# Search tools
if SEARCH_TOOLS_AVAILABLE:
    __all__.extend(['web_search', 'singapore_housing_search'])

# Property tools
if PROPERTY_TOOLS_AVAILABLE:
    __all__.extend(['property_search', 'filter_and_rank_properties', 'scrape_property_details'])

# Financial tools
if FINANCIAL_TOOLS_AVAILABLE:
    __all__.extend([
        'calculate_affordability', 'calculate_loan_repayment',
        'calculate_repayment_duration', 'calculate_cpf_utilization'
    ])

# HTTP tools
if HTTP_TOOLS_AVAILABLE:
    __all__.extend(['enhanced_http_request', 'validate_urls', 'extract_property_metadata'])

# AWS tools
if AWS_TOOLS_AVAILABLE:
    __all__.extend(['aws_rag_search', 'singapore_housing_aws_search', 'validate_aws_rag_configuration'])

# External tools
if EXTERNAL_TOOLS_AVAILABLE:
    __all__.extend(['search_property_portals', 'get_supported_portals', 'validate_portal_configuration'])

# Version and metadata
__version__ = "1.0.0"
__description__ = "Consolidated tools for Singapore Housing AI Assistant"

# System status for debugging
def get_system_status():
    """Get overall system status"""
    return {
        'consolidated_tools': True,
        'registry_available': REGISTRY_AVAILABLE,
        'search_tools': SEARCH_TOOLS_AVAILABLE,
        'property_tools': PROPERTY_TOOLS_AVAILABLE,
        'financial_tools': FINANCIAL_TOOLS_AVAILABLE,
        'http_tools': HTTP_TOOLS_AVAILABLE,
        'aws_tools': AWS_TOOLS_AVAILABLE,
        'external_tools': EXTERNAL_TOOLS_AVAILABLE,
        'version': __version__
    }

# Add system status to exports
__all__.append('get_system_status')

# Log initialization status - FIXED SYNTAX
available_categories = sum([
    REGISTRY_AVAILABLE, SEARCH_TOOLS_AVAILABLE, PROPERTY_TOOLS_AVAILABLE,
    FINANCIAL_TOOLS_AVAILABLE, HTTP_TOOLS_AVAILABLE, AWS_TOOLS_AVAILABLE,
    EXTERNAL_TOOLS_AVAILABLE
])

logger.info(f"Tools consolidated initialized - {available_categories}/7 tool categories available")