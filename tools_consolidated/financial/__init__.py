# tools_consolidated/financial/__init__.py
"""
Consolidated financial tools for affordability calculations, loan analysis, and CPF planning.
"""

from .financial_tools import (
    calculate_affordability,
    calculate_loan_repayment,
    calculate_repayment_duration,
    calculate_cpf_utilization
)

__all__ = [
    'calculate_affordability',
    'calculate_loan_repayment', 
    'calculate_repayment_duration',
    'calculate_cpf_utilization'
]