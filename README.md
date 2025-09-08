# Singapore Housing AI Assistant

A comprehensive agentic solution for Singapore housing guidance, providing intelligent property search, grant eligibility assessment, and personalized recommendations through a multi-agent architecture with AWS RAG integration.

## Overview

This AI assistant leverages multiple specialized agents and consolidated tools to provide comprehensive housing guidance for Singapore residents. The system combines web search capabilities, AWS Knowledge Base integration, financial calculations, and property portal search to deliver accurate, contextual advice.

## Features

### Core Capabilities
- **Multi-Agent Architecture**: Specialized agents for orchestration, property search, grant assessment, filtering, decision support, and content writing
- **AWS RAG Integration**: Knowledge Base search for official Singapore housing policies and regulations
- **Contextual User Management**: Persistent user profiles and journey stage tracking
- **Property Portal Search**: Integration with PropertyGuru, 99.co, HDB.gov.sg, and EdgeProp
- **Financial Calculations**: TDSR compliance, affordability analysis, CPF utilization, and loan calculations
- **Grant Eligibility Assessment**: Comprehensive analysis of available housing grants and subsidies

### Advanced Features
- **Decision Support Engine**: Multi-factor property analysis with risk assessment
- **Consolidated Tool Registry**: Centralized tool management with dependency tracking
- **Enhanced HTTP Client**: Anti-bot measures, rate limiting, and session management
- **URL Validation**: Real-time property listing verification and metadata extraction
- **Caching System**: TTL-based caching for improved performance

## Architecture

### Agent System
```
├── orchestrator_agent.py     # Main coordination agent
├── property_agent.py         # Property search and listings
├── grant_agent.py           # Grant eligibility assessment
├── filter_agent.py          # Property filtering and ranking
├── decision_agent.py        # Comprehensive property analysis
└── writer_agent.py          # Financial calculations and formatting
```

### Consolidated Tools
```
├── tools_consolidated/
│   ├── search/              # Web and Singapore-specific search
│   ├── property/            # Property search and filtering
│   ├── financial/           # Affordability and loan calculations
│   ├── http/               # Enhanced HTTP requests and validation
│   ├── aws/                # AWS Knowledge Base integration
│   ├── external/           # Property portal search
│   └── registry.py         # Central tool management
```

### Core Systems
```
├── core/
│   ├── mcp_context_manager.py    # User context and journey tracking
│   └── decision_support_engine.py # Advanced property analysis
```

## Installation

### Prerequisites
- Python 3.8+
- AWS Account (for Knowledge Base features)
- Valid API keys for external services (optional)

### Dependencies
```bash
pip install -r requirements.txt
```

### Core Dependencies
- `gradio>=4.0.0` - Web interface
- `strands` - Agent framework
- `boto3` - AWS integration
- `python-dotenv` - Environment configuration
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `duckduckgo-search` - Web search

### Optional Dependencies
- `markdownify` - HTML to markdown conversion
- `pandas` - Data manipulation
- `numpy` - Numerical calculations

## Configuration

### Environment Variables
Create a `.env` file with the following configuration:

```bash
# AWS Configuration (Required for full functionality)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_SESSION_TOKEN=your_session_token  # If using temporary credentials
AWS_REGION=us-east-1
AWS_KNOWLEDGE_BASE_ID=your_knowledge_base_id
AWS_DATA_SOURCE_ID=your_data_source_id

# Optional: External Search APIs
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_custom_search_engine_id

# Optional: Cache Configuration
PORTAL_SEARCH_CACHE_TTL=60
PORTAL_SEARCH_CACHE_MAX=200

# Gradio Configuration
GRADIO_ANALYTICS_ENABLED=False
```

### AWS Setup
1. Create an AWS Knowledge Base for Bedrock
2. Upload Singapore housing documents to your S3 data source
3. Configure the Knowledge Base with appropriate permissions
4. Note your Knowledge Base ID and Data Source ID

## Usage

### Starting the Application
```bash
python page.py
```

The application will start on `http://localhost:7860` by default.

### System Status
The application displays real-time system status indicating:
- Consolidated Tools availability
- Context Management status
- AWS RAG connectivity
- Agent system functionality

### Fallback Modes
The system gracefully handles missing dependencies:
- **Full Mode**: All features available with AWS RAG
- **Consolidated Mode**: Local tools without AWS integration
- **Legacy Mode**: Basic functionality with limited features

## API Reference

### Core Tools

#### Search Tools
- `web_search(query, max_results)` - Enhanced web search with site filtering
- `singapore_housing_search(query, search_type)` - Singapore-specific housing search

#### Property Tools
- `property_search(query, max_results, sites)` - Multi-portal property search
- `filter_and_rank_properties(results, criteria)` - Property filtering and ranking
- `validate_urls(listings)` - URL validation and metadata extraction

#### Financial Tools
- `calculate_affordability(income, debt, deposit)` - Comprehensive affordability analysis
- `calculate_loan_repayment(principal, rate, term)` - Detailed loan calculations
- `calculate_cpf_utilization(price, balance, type)` - CPF usage optimization

#### AWS Tools
- `aws_rag_search(query, search_type)` - Knowledge Base search
- `singapore_housing_aws_search(query, domain)` - Domain-specific AWS search
- `validate_aws_rag_configuration()` - System configuration validation

### Agent Interfaces

#### Orchestrator Agent
Central coordination agent that routes queries to appropriate specialized agents and consolidates responses.

#### Property Agent
Handles property search with specific output format:
```json
[
  {
    "name": "Property Name",
    "snippet": "Description",
    "url": "https://...",
    "price": 500000,
    "rooms": 3,
    "location": "Location",
    "ranking_reason": "Explanation"
  }
]
```

#### Grant Agent
Comprehensive grant eligibility assessment following structured workflow:
1. Information collection
2. Official source research
3. Eligibility analysis and recommendations

## Testing

### Sample Queries
- **Property Search**: "Find 3-room HDB flats in Tampines under $500,000"
- **Grant Assessment**: "What housing grants am I eligible for as a Singapore citizen earning $6,000/month?"
- **Financial Analysis**: "Calculate affordability for $8,000 monthly income with $100,000 CPF"

### Validation Tools
```python
# Check system status
from tools_consolidated import get_tool_status, get_system_status

# Validate AWS configuration
from tools_consolidated.aws import validate_aws_rag_configuration
```

## Error Handling

The system implements comprehensive error handling:
- **Graceful Degradation**: Missing dependencies don't break core functionality
- **Fallback Mechanisms**: Alternative tools when primary services unavailable
- **User-Friendly Messages**: Clear error communication without technical jargon
- **Logging**: Detailed logging for debugging and monitoring

## Performance Considerations

- **Caching**: TTL-based caching for property portal searches
- **Rate Limiting**: Respectful crawling with domain-specific delays
- **Session Management**: Persistent HTTP sessions for improved performance
- **Resource Management**: Automatic cleanup and memory management

## Security Features

- **Robots.txt Compliance**: Respects website crawling policies
- **Rate Limiting**: Prevents overwhelming external services
- **Input Validation**: Comprehensive input sanitization
- **Error Isolation**: Prevents cascading failures

## Monitoring and Debugging

### System Status Endpoints
- Real-time tool availability checking
- AWS connectivity validation
- Agent system health monitoring

### Logging Configuration
```python
import logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
```

## Contributing

### Development Setup
1. Clone the repository
2. Install development dependencies
3. Configure environment variables
4. Run tests to verify setup

### Tool Development
New tools should be added to the appropriate category in `tools_consolidated/` and registered in `registry.py`.

### Agent Development
New agents should follow the established pattern and be imported in the orchestrator for coordination.

## License

[Specify your license here]

## Support

For technical support or questions:
- Check system status using built-in validation tools
- Review logs for error details
- Ensure all environment variables are properly configured
- Verify AWS permissions and Knowledge Base access

## Changelog

### Version 1.0.0
- Initial release with full multi-agent architecture
- AWS RAG integration
- Consolidated tool system
- Enhanced property portal search
- Comprehensive financial calculations