# tools.py - Transition compatibility layer
"""
NOTICE: This file provides backward compatibility during migration to consolidated tools.
New development should use tools_consolidated/ directly.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Try to import from consolidated tools first, fallback to legacy implementations
try:
    from tools_consolidated.search import web_search, singapore_housing_search
    from tools_consolidated.property import property_search, filter_and_rank_properties as filter_and_rank
    from tools_consolidated.financial import calculate_affordability, calculate_repayment_duration as repayment_duration
    from tools_consolidated.http import enhanced_http_request as http_request
    
    logger.info("Using consolidated tools via compatibility layer")
    USING_CONSOLIDATED = True
    
except ImportError as e:
    logger.warning(f"Consolidated tools not available, using legacy implementations: {e}")
    USING_CONSOLIDATED = False
    
    # Legacy implementations for absolute fallback
    from duckduckgo_search import DDGS
    import requests
    
    def web_search(query: str, max_results: int = 5):
        """Legacy web search implementation"""
        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=max_results)
            return [{"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")} for r in results]
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def http_request(url: str):
        """Legacy HTTP request implementation"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.text[:2000]
        except Exception as e:
            return f"Request error: {str(e)}"
    
    def property_search(query: str, max_results: int = 5):
        """Legacy property search implementation"""
        return web_search(f"{query} site:propertyguru.com.sg OR site:99.co", max_results)
    
    def filter_and_rank(results, location=None, max_price=None, flat_type=None, k=3):
        """Legacy filter implementation"""
        if not isinstance(results, list):
            return "No results to filter"
        return results[:k]
    
    def singapore_housing_search(query: str, search_type: str = "general", max_results: int = 5):
        """Legacy Singapore housing search"""
        return web_search(f"{query} Singapore site:hdb.gov.sg OR site:cpf.gov.sg", max_results)
    
    def calculate_affordability(monthly_income: float, existing_debt: float = 0, deposit_saved: float = 0):
        """Legacy affordability calculation"""
        try:
            max_payment = monthly_income * 0.30 - existing_debt
            return f"Max monthly payment: ${max_payment:,.2f}"
        except:
            return "Error calculating affordability"
    
    def repayment_duration(principal: float, monthly_payment: float):
        """Legacy repayment duration calculation"""
        try:
            months = principal / monthly_payment
            years = int(months // 12)
            rem_months = int(months % 12)
            return f"{years} years and {rem_months} months"
        except:
            return "Error calculating duration"

# Export all functions for backward compatibility
__all__ = [
    'web_search', 'singapore_housing_search', 'property_search', 
    'filter_and_rank', 'calculate_affordability', 'repayment_duration', 
    'http_request'
]

# Deprecation warning function
def _warn_legacy_usage(func_name: str):
    """Warn about legacy usage"""
    if USING_CONSOLIDATED:
        logger.info(f"Function {func_name} called via compatibility layer - consider updating imports")