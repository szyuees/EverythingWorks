# core/__init__.py
"""
Core system components for the Singapore Housing AI Assistant.
"""

try:
    from .mcp_context_manager import MCPContextManager
    MCP_AVAILABLE = True
except ImportError:
    MCPContextManager = None
    MCP_AVAILABLE = False

try:
    from .decision_support_engine import DecisionSupportEngine, PropertyOption
    DECISION_ENGINE_AVAILABLE = True
except ImportError:
    DecisionSupportEngine = None
    PropertyOption = None
    DECISION_ENGINE_AVAILABLE = False

__all__ = []
if MCP_AVAILABLE:
    __all__.extend(['MCPContextManager'])
if DECISION_ENGINE_AVAILABLE:
    __all__.extend(['DecisionSupportEngine', 'PropertyOption'])