# agents/__init__.py
"""
Agent modules for the Singapore Housing AI Assistant.
"""

# Core agents
try:
    from .orchestrator_agent import orchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    orchestrator = None
    ORCHESTRATOR_AVAILABLE = False

try:
    from .property_agent import property_agent
    PROPERTY_AGENT_AVAILABLE = True
except ImportError:
    property_agent = None
    PROPERTY_AGENT_AVAILABLE = False

try:
    from .grant_agent import grant_agent
    GRANT_AGENT_AVAILABLE = True
except ImportError:
    grant_agent = None
    GRANT_AGENT_AVAILABLE = False

try:
    from .filter_agent import filter_agent
    FILTER_AGENT_AVAILABLE = True
except ImportError:
    filter_agent = None
    FILTER_AGENT_AVAILABLE = False

try:
    from .writer_agent import writer_agent
    WRITER_AGENT_AVAILABLE = True
except ImportError:
    writer_agent = None
    WRITER_AGENT_AVAILABLE = False

try:
    from .decision_agent import decision_agent
    DECISION_AGENT_AVAILABLE = True
except ImportError:
    decision_agent = None
    DECISION_AGENT_AVAILABLE = False

__all__ = []
if ORCHESTRATOR_AVAILABLE:
    __all__.append('orchestrator')
if PROPERTY_AGENT_AVAILABLE:
    __all__.append('property_agent')
if GRANT_AGENT_AVAILABLE:
    __all__.append('grant_agent')
if FILTER_AGENT_AVAILABLE:
    __all__.append('filter_agent')
if WRITER_AGENT_AVAILABLE:
    __all__.append('writer_agent')
if DECISION_AGENT_AVAILABLE:
    __all__.append('decision_agent')