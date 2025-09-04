from strands import tool
from duckduckgo_search import DDGS
import requests
import logging
import os

# RAG imports with error handling
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError as e:
    logging.warning(f"RAG dependencies not available: {e}")
    chromadb = None
    SentenceTransformer = None
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

# Basic web search and HTTP tools (core functionality)
@tool
def web_search(query: str, max_results: int = 5):
    """Search the web using DuckDuckGo with error handling."""
    try:
        results = []
        search_results = DDGS().text(query, max_results=max_results)
        
        for item in search_results:
            result = {
                "title": item.get("title", ""),
                "snippet": item.get("body", ""),
                "link": item.get("href", "")
            }
            results.append(result)
            
        return results if results else "No results found."
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Web search error: {str(e)}"

@tool
def http_request(url: str):
    """Perform HTTP GET request with error handling."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Return first 2000 chars for better context
        return response.text[:2000]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request error for {url}: {e}")
        return f"Error fetching URL {url}: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return f"Unexpected error fetching URL {url}: {str(e)}"

@tool
def filter_and_rank(results, location=None, max_price=None, flat_type=None, k=3):
    """Filter search results by criteria and return top-k with error handling."""
    try:
        if not isinstance(results, list):
            return "Invalid input: results must be a list"
        
        if not results:
            return "No results to filter"
        
        # Simple filtering logic - in production, implement more sophisticated filtering
        filtered_results = results.copy()
        
        # Apply location filter if specified
        if location:
            location_lower = location.lower()
            filtered_results = [
                r for r in filtered_results 
                if any(location_lower in str(v).lower() for v in r.values())
            ]
        
        # Apply price filter if specified (basic implementation)
        if max_price:
            try:
                max_price_num = float(max_price)
                # This is a simplified implementation
                filtered_results = [
                    r for r in filtered_results 
                    if not any(
                        str(max_price_num) in str(v) and 'price' in str(k).lower() 
                        for k, v in r.items()
                    )
                ]
            except ValueError:
                logger.warning(f"Invalid max_price format: {max_price}")
        
        # Return top k results
        return filtered_results[:k] if filtered_results else "No results match the criteria"
        
    except Exception as e:
        logger.error(f"Filter and rank error: {e}")
        return f"Error filtering results: {str(e)}"

@tool
def repayment_duration(principal: float, monthly_payment: float) -> str:
    """Compute repayment duration in years and months with error handling."""
    try:
        principal = float(principal)
        monthly_payment = float(monthly_payment)
        
        if monthly_payment <= 0:
            return "Monthly payment must be greater than 0"
        
        if principal <= 0:
            return "Principal amount must be greater than 0"
        
        months = principal / monthly_payment
        years = int(months // 12)
        rem_months = int(months % 12)
        
        if years > 0:
            return f"{years} years and {rem_months} months"
        else:
            return f"{rem_months} months"
            
    except (ValueError, TypeError) as e:
        return f"Invalid input for calculation: {str(e)}"
    except Exception as e:
        logger.error(f"Repayment calculation error: {e}")
        return f"Error calculating repayment duration: {str(e)}"

# RAG tools with comprehensive error handling
@tool
def initialize_rag_system():
    """Initialize RAG knowledge base with comprehensive error handling"""
    if not RAG_AVAILABLE:
        return "RAG system dependencies not available. Install chromadb and sentence-transformers."
    
    try:
        # Create data directory if it doesn't exist
        os.makedirs("./data/vector_store", exist_ok=True)
        
        client = chromadb.PersistentClient(path="./data/vector_store")
        
        # Create collections if they don't exist
        collections = ["hdb_policies", "grant_schemes", "market_data", "location_intel"]
        created_collections = []
        existing_collections = []
        
        for collection_name in collections:
            try:
                collection = client.get_collection(collection_name)
                existing_collections.append(collection_name)
                logger.info(f"Collection {collection_name} already exists")
            except Exception:
                try:
                    collection = client.create_collection(collection_name)
                    created_collections.append(collection_name)
                    logger.info(f"Created collection {collection_name}")
                except Exception as e:
                    logger.error(f"Failed to create collection {collection_name}: {e}")
        
        status_message = f"RAG system initialized. "
        if created_collections:
            status_message += f"Created: {', '.join(created_collections)}. "
        if existing_collections:
            status_message += f"Existing: {', '.join(existing_collections)}."
        
        return status_message
        
    except Exception as e:
        logger.error(f"RAG initialization error: {e}")
        return f"RAG initialization failed: {str(e)}"

@tool  
def rag_search(query: str, collection_name: str = "hdb_policies", top_k: int = 3):
    """Search RAG knowledge base with comprehensive error handling"""
    if not RAG_AVAILABLE:
        return "RAG search not available. Missing dependencies: chromadb, sentence-transformers."
    
    try:
        # Validate inputs
        if not query or not query.strip():
            return "Empty query provided"
        
        if not collection_name:
            collection_name = "hdb_policies"
        
        if top_k <= 0:
            top_k = 3
        
        client = chromadb.PersistentClient(path="./data/vector_store")
        
        try:
            collection = client.get_collection(collection_name)
        except Exception as e:
            logger.warning(f"Collection {collection_name} not found: {e}")
            return f"Knowledge base collection '{collection_name}' not found. Please initialize the RAG system first."
        
        # Check if collection has any documents
        try:
            count = collection.count()
            if count == 0:
                return f"Knowledge base collection '{collection_name}' is empty. Please populate with data first."
        except Exception as e:
            logger.warning(f"Could not check collection count: {e}")
        
        # For now, return placeholder until actual data is populated
        return f"RAG Search Results for '{query}' in {collection_name}: [System initialized but requires data population with official HDB/CPF documents]"
        
    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return f"RAG search failed: {str(e)}"

# Utility function for safe data processing
def safe_extract_text(content, max_length=1000):
    """Safely extract text content with length limits"""
    try:
        if not content:
            return ""
        
        text = str(content)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
        
    except Exception as e:
        logger.error(f"Text extraction error: {e}")
        return f"Error extracting text: {str(e)}"

# Enhanced search with Singapore-specific filtering
@tool
def singapore_housing_search(query: str, search_type: str = "general", max_results: int = 5):
    """Enhanced search specifically for Singapore housing with domain filtering"""
    try:
        # Add Singapore context to query
        sg_query = f"{query} Singapore"
        
        # Add domain-specific terms based on search type
        if search_type == "grants":
            sg_query += " HDB grants CPF housing scheme site:hdb.gov.sg OR site:cpf.gov.sg"
        elif search_type == "policies":
            sg_query += " HDB policy eligibility site:hdb.gov.sg OR site:gov.sg"
        elif search_type == "properties":
            sg_query += " HDB flat property site:propertyguru.com.sg OR site:99.co OR site:hdb.gov.sg"
        
        results = web_search(sg_query, max_results)
        
        # Filter results to prioritize official Singapore sources
        if isinstance(results, list):
            prioritized = []
            regular = []
            
            official_domains = ['hdb.gov.sg', 'cpf.gov.sg', 'gov.sg', 'ura.gov.sg']
            
            for result in results:
                link = result.get('link', '').lower()
                if any(domain in link for domain in official_domains):
                    prioritized.append(result)
                else:
                    regular.append(result)
            
            # Return prioritized official sources first
            return prioritized + regular
        
        return results
        
    except Exception as e:
        logger.error(f"Singapore housing search error: {e}")
        return f"Search error: {str(e)}"

# Financial calculation tools
@tool
def calculate_affordability(monthly_income: float, existing_debt: float = 0, deposit_saved: float = 0):
    """Calculate housing affordability based on Singapore guidelines"""
    try:
        monthly_income = float(monthly_income)
        existing_debt = float(existing_debt)
        deposit_saved = float(deposit_saved)
        
        if monthly_income <= 0:
            return "Monthly income must be greater than 0"
        
        # Singapore banks typically use 30% debt-to-income ratio
        max_monthly_payment = monthly_income * 0.30
        available_for_housing = max_monthly_payment - existing_debt
        
        if available_for_housing <= 0:
            return "Current debt obligations exceed recommended housing affordability ratio"
        
        # Estimate property value based on monthly payment (rough calculation)
        # Assuming 2.5% interest rate, 25-year loan
        estimated_loan_amount = available_for_housing * 12 * 20  # Simplified calculation
        estimated_property_value = estimated_loan_amount + deposit_saved
        
        return {
            "max_monthly_payment": round(available_for_housing, 2),
            "estimated_budget_range": f"${estimated_property_value:,.0f}",
            "recommended_deposit": round(estimated_property_value * 0.20, 2),
            "monthly_income_used": f"{(available_for_housing / monthly_income) * 100:.1f}%"
        }
        
    except (ValueError, TypeError) as e:
        return f"Invalid input for affordability calculation: {str(e)}"
    except Exception as e:
        logger.error(f"Affordability calculation error: {e}")
        return f"Error calculating affordability: {str(e)}"