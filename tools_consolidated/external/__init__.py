# tools_consolidated/external/__init__.py
"""
External API and service integration tools.
Includes portal search functionality and third-party service integrations.
"""

try:
    from .portal_search_tools import (
        search_property_portals,
        get_supported_portals,
        validate_portal_configuration,
        search_portals  # Backward compatibility alias
    )
    EXTERNAL_TOOLS_AVAILABLE = True
    __all__ = [
        'search_property_portals',
        'get_supported_portals', 
        'validate_portal_configuration',
        'search_portals'
    ]
except ImportError as e:
    EXTERNAL_TOOLS_AVAILABLE = False
    __all__ = []