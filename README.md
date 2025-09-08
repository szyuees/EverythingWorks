# Singapore Housing AI Assistant

A sophisticated multi-agent artificial intelligence solution designed to provide comprehensive housing guidance for Singapore residents. This system leverages advanced agent architecture, AWS Retrieval-Augmented Generation (RAG), and real-time property data integration to deliver intelligent property recommendations, grant eligibility assessments, and financial analysis.

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Features](#features)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

## Overview

The Singapore Housing AI Assistant is an enterprise-grade agentic solution that addresses the complexity of Singapore's housing market through intelligent automation. The system combines multiple specialized agents with comprehensive data sources to provide accurate, contextual housing guidance.

### Key Capabilities

- **Multi-Agent Orchestration**: Coordinated specialist agents for different aspects of housing guidance
- **Real-Time Property Search**: Integration with major Singapore property portals (PropertyGuru, 99.co, HDB.gov.sg, EdgeProp)
- **Grant Intelligence**: Automated assessment of housing grants and subsidies eligibility
- **Financial Modeling**: TDSR compliance checking, affordability analysis, and CPF utilization optimization
- **Knowledge Base Integration**: AWS-powered RAG system with official Singapore housing policies

## System Architecture

### Directory Structure

```
singapore-housing-ai-assistant/
├── .env                           # Environment configuration
├── aws_session.py                 # AWS session management
├── page.py                        # Main Gradio application
├── requirements.txt               # Python dependencies
├── tools.py                       # Legacy compatibility layer
│
├── agents/                        # Multi-agent system
│   ├── __init__.py
│   ├── orchestrator_agent.py      # Central coordination agent
│   ├── property_agent.py          # Property search specialist
│   ├── grant_agent.py             # Grant eligibility specialist
│   ├── filter_agent.py            # Property filtering specialist
│   ├── decision_agent.py          # Decision support specialist
│   └── writer_agent.py            # Financial calculations specialist
│
├── core/                          # Core business logic
│   ├── __init__.py
│   ├── decision_support_engine.py # Advanced property analysis
│   └── mcp_context_manager.py     # User context management
│
└── tools_consolidated/            # Organized tool system
    ├── __init__.py
    ├── registry.py                # Central tool registry
    │
    ├── aws/                       # AWS integration tools
    │   ├── __init__.py
    │   └── aws_tools.py           # Knowledge Base RAG search
    │
    ├── external/                  # External service integration
    │   ├── __init__.py
    │   └── portal_search_tools.py # Property portal search
    │
    ├── financial/                 # Financial calculation tools
    │   ├── __init__.py
    │   └── financial_tools.py     # Affordability, CPF, loans
    │
    ├── http/                      # HTTP and web tools
    │   ├── __init__.py
    │   └── http_tools.py          # Web scraping, validation
    │
    ├── property/                  # Property-specific tools
    │   ├── __init__.py
    │   └── property_tools.py      # Search, filter, scrape
    │
    └── search/                    # Search tools
        ├── __init__.py
        └── search_tools.py        # Web search, Singapore search
```

### Agent Ecosystem

```
┌─────────────────────────────────────────────────────────┐
│                 Orchestrator Agent                      │
│              (Central Coordination)                     │
└─────────────────┬───────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐    ┌───▼───┐    ┌───▼───┐
│Property│    │ Grant │    │Filter │
│ Agent  │    │ Agent │    │ Agent │
└────────┘    └───────┘    └───────┘
    │             │             │
┌───▼───┐    ┌───▼───┐         │
│Decision│    │Writer │         │
│ Agent  │    │ Agent │         │
└───────┘    └───────┘         │
                               │
┌─────────────────────────────▼─────────────────────────┐
│              Consolidated Tools                       │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐   │
│  │ Search  │ │ Property │ │Financial │ │   AWS   │   │
│  │  Tools  │ │  Tools   │ │  Tools   │ │  Tools  │   │
│  └─────────┘ └──────────┘ └──────────┘ └─────────┘   │
└───────────────────────────────────────────────────────┘
```

### Technology Stack

- **Agent Framework**: Strands
- **Web Interface**: Gradio 4.0+
- **Cloud Integration**: AWS Bedrock Knowledge Base
- **Data Processing**: Pandas, NumPy
- **Web Scraping**: BeautifulSoup4, Requests
- **Search Integration**: DDGS (DuckDuckGo Search)
- **HTTP Client**: Enhanced session management with anti-bot measures
- **Caching**: TTL-based in-memory cache with LRU eviction

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB available disk space

### Required Accounts and Access

- **AWS Account**: For Knowledge Base functionality
- **Internet Connection**: For real-time property data retrieval

### Optional Enhancements

- **Google Search API**: For enhanced search capabilities
- **External APIs**: Additional property data sources

## Installation

### 1. Clone Repository

```bash
git clone [your-repository-url]
cd singapore-housing-ai-assistant
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### Core Dependencies

```
gradio>=4.0.0
strands
boto3
python-dotenv
requests
beautifulsoup4==4.12.2
ddgs
markdownify
urllib3
pandas
numpy
```

## Configuration

###  Environment Variables

Create a `.env` file in the project root:

```env
# AWS Configuration (Required for full functionality)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_SESSION_TOKEN=your_session_token  
AWS_REGION=us-east-1
AWS_KNOWLEDGE_BASE_ID=your_knowledge_base_id
AWS_DATA_SOURCE_ID=your_data_source_id

GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_custom_search_engine_id

```

## Quick Start

### 1. Launch Application

```bash
python page.py
```

The application will be available at `http://localhost:7860`

### 2. System Status Check

Upon startup, the interface displays real-time system status:

```bash
INFO | main | Starting Enhanced Housing Assistant with Consolidated Tools
INFO | tools_consolidated.registry | Python environment: conda - C:\Users\wuche\anaconda3\envs\agentic-env\python.exe
INFO | tools_consolidated.registry | Initializing tool registry with environment awareness...
INFO | botocore.credentials | Found credentials in environment variables.
INFO | tools_consolidated.aws.aws_tools | AWS clients initialized for KB: AVGJILOX4X
INFO | tools_consolidated.aws.aws_tools | AWS Knowledge Base manager initialized successfully
INFO | tools_consolidated.search.search_tools | AWS RAG tools loaded from consolidated location
INFO | tools_consolidated.property.property_tools | Portal search tools loaded successfully
INFO | tools_consolidated.property.property_tools | HTTP tools loaded successfully
INFO | tools_consolidated.registry | BeautifulSoup4 status: Available as bs4
INFO | tools_consolidated.registry | Using full HTTP tools with BeautifulSoup4
INFO | tools_consolidated.registry | AWS RAG tools registered successfully
INFO | tools_consolidated.registry | External service tools registered successfully
INFO | tools_consolidated.registry | Tool registry initialized with 18 tools
INFO | tools_consolidated.registry | Tool Status: 18/18 available
INFO | tools_consolidated.registry |   search: 2/2 available
INFO | tools_consolidated.registry |   property: 3/3 available
INFO | tools_consolidated.registry |   financial: 4/4 available
INFO | tools_consolidated.registry |   http: 3/3 available
INFO | tools_consolidated.registry |   aws: 3/3 available
INFO | tools_consolidated.registry |   external: 3/3 available
INFO | tools_consolidated.registry | Environment: conda
INFO | tools_consolidated | Tools consolidated initialized - 7/7 tool categories available
INFO | main | Consolidated tools loaded successfully
INFO | main | Tool Status: 18/18 tools available
INFO | agents.orchestrator_agent | Consolidated tools imported successfully
INFO | agents.orchestrator_agent | AWS RAG tools imported successfully
INFO | botocore.credentials | Found credentials in environment variables.
INFO | botocore.credentials | Found credentials in environment variables.
INFO | botocore.credentials | Found credentials in environment variables.
INFO | botocore.credentials | Found credentials in environment variables.
INFO | botocore.credentials | Found credentials in environment variables.
INFO | botocore.credentials | Found credentials in environment variables.
INFO | agents.orchestrator_agent | Orchestrator initialized with 13 tools
INFO | agents.orchestrator_agent | ✅ Using consolidated tools
INFO | agents.orchestrator_agent | ✅ Decision analysis agent available
INFO | agents.orchestrator_agent | ✅ AWS RAG search available
INFO | agents.orchestrator_agent | ✅ Agent system available
INFO | main | Orchestrator agent loaded
INFO | main | MCP Context Manager available
INFO | core.mcp_context_manager | MCPContextManager initialized
INFO | main | MCP Context Manager initialized
INFO | main | Enhanced chatbot with context management initialized
INFO | main | Launching Enhanced Singapore Housing Assistant
INFO | main | Active Features: Consolidated Tools, Context Management
```

### 3. Test Basic Functionality

Select quick start queries to verify system functionality:

```
"What housing grants am I eligible for as a Singapore citizen?"
"I earn $6000/month, what's my housing budget?"
"Can you provide a list of flats that are suitable for me?"
```

## Features

### Property Search and Analysis

- **Multi-Portal Integration**: Simultaneous search across major property platforms
- **Advanced Filtering**: Price range, location, property type, and amenity filtering
- **Ranking Algorithm**: Intelligent property ranking based on user criteria
- **URL Validation**: Real-time verification of property listing accuracy

### Grant and Subsidy Assessment

- **Eligibility Analysis**: Comprehensive assessment of available housing grants
- **Document Research**: Integration with official government sources
- **Personalized Recommendations**: Tailored grant suggestions based on user profile
- **Application Guidance**: Step-by-step application process assistance

### Financial Modeling

- **Affordability Calculator**: TDSR-compliant affordability assessment
- **Loan Analysis**: Detailed repayment calculations with multiple scenarios
- **CPF Optimization**: Strategic CPF utilization recommendations
- **Risk Assessment**: Comprehensive financial risk analysis

### AWS S3 Bucket & Knowledge Base Integration for RAG Pipeline

- **Official Policies**: Access to current Singapore housing regulations
- **Real-Time Updates**: Dynamic integration with government policy changes
- **Contextual Guidance**: Policy-aware recommendations and advice
- **Compliance Checking**: Automated regulatory compliance verification

## API Documentation

### Core Search Functions

#### `web_search(query, max_results=10)`
Enhanced web search with Singapore-specific filtering.

**Parameters:**
- `query` (str): Search query
- `max_results` (int): Maximum results to return

**Returns:** List of search results with metadata

#### `property_search(query, max_results=20, sites=None)`
Multi-platform property search.

**Parameters:**
- `query` (str): Property search criteria
- `max_results` (int): Maximum listings to return
- `sites` (list): Specific sites to search

**Returns:** Structured property listings

### Financial Analysis Functions

#### `calculate_affordability(income, debt, deposit)`
Comprehensive affordability analysis.

**Parameters:**
- `income` (float): Monthly gross income
- `debt` (float): Existing monthly debt obligations
- `deposit` (float): Available deposit amount

**Returns:** Detailed affordability assessment

#### `calculate_cpf_utilization(price, balance, property_type)`
CPF usage optimization.

**Parameters:**
- `price` (float): Property price
- `balance` (dict): CPF account balances
- `property_type` (str): HDB/Private property type

**Returns:** Optimized CPF utilization strategy

### AWS Integration Functions

#### `aws_rag_search(query, search_type="SEMANTIC")`
Knowledge Base search for official policies.

**Parameters:**
- `query` (str): Search query
- `search_type` (str): SEMANTIC or HYBRID search

**Returns:** Policy-relevant information with sources

## Testing

### User Acceptance Testing Scenarios

1. **First-Time Buyer Journey**
   ```
   Input: "I'm 28, Singapore citizen, earning $5500/month, looking for my first home"
   Expected: Profile collection → Grant assessment → Property recommendations → Financial analysis
   ```

2. **Property Upgrade Scenario**  
   ```
   Input: "Current 3-room HDB owner, want to upgrade to 4-room, budget $600k"
   Expected: Upgrade eligibility → Property search → Financial comparison → Timeline guidance
   ```

3. **Investment Property Analysis**
   ```
   Input: "Looking for investment property, budget $1.2M, rental yield analysis"
   Expected: Investment-focused search → Yield calculations → Market analysis → Risk assessment
   ```

