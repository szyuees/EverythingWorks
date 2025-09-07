# tools_consolidated/financial/financial_tools.py
import logging
from typing import Dict, List, Any, Optional
from strands import tool
import math

logger = logging.getLogger(__name__)

@tool
def calculate_affordability(monthly_income: float, existing_debt: float = 0, 
                          deposit_saved: float = 0) -> Dict[str, Any]:
    """Enhanced affordability calculation with Singapore guidelines"""
    try:
        monthly_income = float(monthly_income)
        existing_debt = float(existing_debt)
        deposit_saved = float(deposit_saved)
        
        if monthly_income <= 0:
            return {"error": "Monthly income must be greater than 0"}
        
        # Singapore-specific affordability calculations
        # TDSR (Total Debt Servicing Ratio) is 60% for most cases
        max_total_monthly_payment = monthly_income * 0.60
        available_for_housing = max_total_monthly_payment - existing_debt
        
        if available_for_housing <= 0:
            return {
                "error": "Current debt obligations exceed TDSR limits",
                "max_tdsr": round(max_total_monthly_payment, 2),
                "current_debt": existing_debt
            }
        
        # Conservative housing affordability (30% of gross income)
        conservative_housing_budget = monthly_income * 0.30
        recommended_payment = min(available_for_housing, conservative_housing_budget)
        
        # Estimate property value (assuming 2.6% interest, 25-year loan)
        loan_multiplier = 280  # Approximation for 25-year loan at 2.6%
        estimated_loan_amount = recommended_payment * loan_multiplier
        estimated_property_value = estimated_loan_amount + deposit_saved
        
        # HDB vs Private thresholds (2024 figures)
        hdb_income_ceiling = 14000
        can_buy_hdb = monthly_income <= hdb_income_ceiling
        
        return {
            "max_monthly_payment": round(recommended_payment, 2),
            "estimated_budget_range": f"${estimated_property_value:,.0f}",
            "recommended_deposit": round(estimated_property_value * 0.25, 2),
            "income_utilization": f"{(recommended_payment / monthly_income) * 100:.1f}%",
            "tdsr_utilization": f"{((existing_debt + recommended_payment) / monthly_income) * 100:.1f}%",
            "hdb_eligible": can_buy_hdb,
            "property_types": ["HDB", "EC", "Private"] if not can_buy_hdb else ["HDB", "EC"],
            "recommendations": _generate_affordability_recommendations(
                monthly_income, recommended_payment, estimated_property_value, can_buy_hdb
            )
        }
        
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for affordability calculation: {str(e)}"}
    except Exception as e:
        logger.error(f"Affordability calculation error: {e}")
        return {"error": f"Error calculating affordability: {str(e)}"}

@tool
def calculate_loan_repayment(principal: float, annual_interest_rate: float, 
                           loan_term_years: int) -> Dict[str, Any]:
    """Calculate detailed loan repayment information"""
    try:
        principal = float(principal)
        annual_interest_rate = float(annual_interest_rate)
        loan_term_years = int(loan_term_years)
        
        if principal <= 0 or annual_interest_rate < 0 or loan_term_years <= 0:
            return {"error": "All loan parameters must be positive"}
        
        # Monthly calculations
        monthly_rate = annual_interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        # Monthly payment calculation (if interest rate > 0)
        if monthly_rate > 0:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                            ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = principal / num_payments
        
        total_payment = monthly_payment * num_payments
        total_interest = total_payment - principal
        
        # Generate payment schedule (first year)
        payment_schedule = []
        remaining_balance = principal
        
        for month in range(1, min(13, num_payments + 1)):  # First 12 months
            interest_payment = remaining_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment
            remaining_balance -= principal_payment
            
            payment_schedule.append({
                "month": month,
                "monthly_payment": round(monthly_payment, 2),
                "principal_payment": round(principal_payment, 2),
                "interest_payment": round(interest_payment, 2),
                "remaining_balance": round(remaining_balance, 2)
            })
        
        return {
            "monthly_payment": round(monthly_payment, 2),
            "total_payment": round(total_payment, 2),
            "total_interest": round(total_interest, 2),
            "interest_percentage": f"{(total_interest / principal) * 100:.1f}%",
            "payment_schedule_first_year": payment_schedule,
            "loan_summary": {
                "principal": principal,
                "interest_rate": f"{annual_interest_rate}%",
                "term": f"{loan_term_years} years",
                "monthly_payment": round(monthly_payment, 2)
            }
        }
        
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for loan calculation: {str(e)}"}
    except Exception as e:
        logger.error(f"Loan calculation error: {e}")
        return {"error": f"Error calculating loan: {str(e)}"}

@tool
def calculate_repayment_duration(principal: float, monthly_payment: float) -> Dict[str, Any]:
    """Calculate how long it takes to repay a loan with given monthly payments"""
    try:
        principal = float(principal)
        monthly_payment = float(monthly_payment)
        
        if monthly_payment <= 0:
            return {"error": "Monthly payment must be greater than 0"}
        
        if principal <= 0:
            return {"error": "Principal amount must be greater than 0"}
        
        # Simple calculation without interest (for basic estimation)
        months = principal / monthly_payment
        years = int(months // 12)
        remaining_months = int(months % 12)
        
        result_text = []
        if years > 0:
            result_text.append(f"{years} years")
        if remaining_months > 0:
            result_text.append(f"{remaining_months} months")
        
        duration_text = " and ".join(result_text) if result_text else "Less than 1 month"
        
        return {
            "duration_text": duration_text,
            "total_months": int(months),
            "years": years,
            "remaining_months": remaining_months,
            "total_paid": monthly_payment * months,
            "note": "Calculation assumes no interest (for basic estimation)"
        }
        
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for calculation: {str(e)}"}
    except Exception as e:
        logger.error(f"Repayment duration calculation error: {e}")
        return {"error": f"Error calculating duration: {str(e)}"}

@tool
def calculate_cpf_utilization(property_price: float, cpf_oa_balance: float, 
                            property_type: str = "HDB") -> Dict[str, Any]:
    """Calculate CPF Ordinary Account utilization for property purchase"""
    try:
        property_price = float(property_price)
        cpf_oa_balance = float(cpf_oa_balance)
        
        if property_price <= 0 or cpf_oa_balance < 0:
            return {"error": "Invalid property price or CPF balance"}
        
        # CPF usage limits (2024 guidelines)
        cpf_limits = {
            "HDB": {
                "down_payment_limit": 0.20,  # Up to 20% down payment
                "monthly_limit": 0.80,       # Up to 80% of monthly installment
                "total_limit": None          # No specific limit for HDB
            },
            "Private": {
                "down_payment_limit": 0.05,  # Up to 5% down payment
                "monthly_limit": 0.80,       # Up to 80% of monthly installment
                "total_limit": property_price * 0.80  # Total usage limit
            },
            "EC": {
                "down_payment_limit": 0.20,  # Up to 20% down payment  
                "monthly_limit": 0.80,       # Up to 80% of monthly installment
                "total_limit": None          # No specific limit for EC
            }
        }
        
        limits = cpf_limits.get(property_type.upper(), cpf_limits["HDB"])
        
        # Calculate down payment requirements
        min_down_payment = property_price * 0.05 if property_type.upper() == "Private" else property_price * 0.10
        max_cpf_down_payment = property_price * limits["down_payment_limit"]
        
        # Calculate how much CPF can be used for down payment
        cpf_for_down_payment = min(cpf_oa_balance, max_cpf_down_payment, min_down_payment)
        cash_down_payment = min_down_payment - cpf_for_down_payment
        
        # Remaining CPF after down payment
        remaining_cpf = cpf_oa_balance - cpf_for_down_payment
        
        # Loan amount
        loan_amount = property_price - min_down_payment
        
        return {
            "property_price": property_price,
            "property_type": property_type,
            "down_payment_breakdown": {
                "total_down_payment": min_down_payment,
                "cpf_down_payment": round(cpf_for_down_payment, 2),
                "cash_down_payment": round(cash_down_payment, 2)
            },
            "cpf_utilization": {
                "initial_cpf_balance": cpf_oa_balance,
                "cpf_used_for_down_payment": round(cpf_for_down_payment, 2),
                "remaining_cpf_balance": round(remaining_cpf, 2),
                "max_monthly_cpf_usage": f"80% of monthly installment"
            },
            "loan_details": {
                "loan_amount": round(loan_amount, 2),
                "estimated_monthly_payment": round(loan_amount * 0.004, 2)  # Rough estimate
            },
            "recommendations": _generate_cpf_recommendations(
                cpf_for_down_payment, remaining_cpf, property_type
            )
        }
        
    except (ValueError, TypeError) as e:
        return {"error": f"Invalid input for CPF calculation: {str(e)}"}
    except Exception as e:
        logger.error(f"CPF calculation error: {e}")
        return {"error": f"Error calculating CPF utilization: {str(e)}"}

def _generate_affordability_recommendations(income: float, monthly_payment: float, 
                                          property_value: float, hdb_eligible: bool) -> List[str]:
    """Generate personalized affordability recommendations"""
    recommendations = []
    
    if monthly_payment / income > 0.25:
        recommendations.append("Consider a lower budget to maintain financial flexibility")
    
    if hdb_eligible:
        recommendations.append("You're eligible for HDB flats - consider BTO vs resale options")
        recommendations.append("Check for available housing grants to reduce purchase cost")
    else:
        recommendations.append("Explore Executive Condominiums (EC) as a middle option")
        recommendations.append("Private property limits CPF usage - ensure sufficient cash reserves")
    
    if property_value > income * 60:  # Property price > 5 years income
        recommendations.append("Consider a longer loan tenure to reduce monthly payments")
    
    recommendations.append("Get pre-approval for housing loan to confirm actual budget")
    recommendations.append("Set aside emergency fund equivalent to 6 months of expenses")
    
    return recommendations

def _generate_cpf_recommendations(cpf_used: float, remaining_cpf: float, 
                                property_type: str) -> List[str]:
    """Generate CPF utilization recommendations"""
    recommendations = []
    
    if remaining_cpf > 50000:
        recommendations.append("You have substantial CPF remaining for monthly payments")
    elif remaining_cpf < 10000:
        recommendations.append("Consider preserving more CPF for retirement - increase cash portion")
    
    if property_type.upper() == "PRIVATE":
        recommendations.append("Private property limits CPF usage - plan for higher cash requirements")
    
    recommendations.append("Remember: CPF used for property must be returned upon sale with accrued interest")
    recommendations.append("Consider the impact on your CPF retirement savings")
    
    return recommendations