# tools_consolidated/aws/__init__.py
"""
AWS tools for Knowledge Base search and document management.
"""

try:
    from .aws_tools import (
        aws_rag_search,
        singapore_housing_aws_search, 
        validate_aws_rag_configuration,
        get_aws_status
    )
    AWS_TOOLS_AVAILABLE = True
    __all__ = [
        'aws_rag_search',
        'singapore_housing_aws_search',
        'validate_aws_rag_configuration', 
        'get_aws_status'
    ]
except ImportError as e:
    AWS_TOOLS_AVAILABLE = False
    __all__ = []