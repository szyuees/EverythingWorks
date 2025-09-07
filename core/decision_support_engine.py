# decision_support_engine.py
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from aws_session import session

class DecisionFactor(Enum):
    AFFORDABILITY = "affordability"
    LOCATION_CONVENIENCE = "location_convenience"
    INVESTMENT_POTENTIAL = "investment_potential"
    LIFESTYLE_FIT = "lifestyle_fit"
    GRANT_ELIGIBILITY = "grant_eligibility"
    TIMING = "timing"

@dataclass
class PropertyOption:
    """Represents a property option with all relevant data"""
    property_id: str
    address: str
    price: float
    property_type: str  # HDB/Condo/EC
    size_sqft: int
    rooms: str
    age: int
    mrt_distance_m: int
    school_rating: float  # 1-10
    amenities_score: float  # 1-10
    resale_potential: float  # 1-10
    available_grants: List[Dict[str, Any]]
    monthly_repayment: float
    total_cost_including_grants: float

class DecisionSupportEngine:
    """Advanced decision support for housing choices"""
    
    def __init__(self):
        self.factor_weights = {
            DecisionFactor.AFFORDABILITY: 0.25,
            DecisionFactor.LOCATION_CONVENIENCE: 0.20,
            DecisionFactor.INVESTMENT_POTENTIAL: 0.15,
            DecisionFactor.LIFESTYLE_FIT: 0.20,
            DecisionFactor.GRANT_ELIGIBILITY: 0.15,
            DecisionFactor.TIMING: 0.05
        }
    
    def analyze_options(self, properties: List[PropertyOption], 
                       user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive analysis of property options"""
        
        if not properties:
            return {"error": "No properties to analyze"}
        
        analysis_results = []
        
        for prop in properties:
            scores = self._calculate_factor_scores(prop, user_profile)
            overall_score = self._calculate_weighted_score(scores)
            
            analysis_results.append({
                "property": prop,
                "factor_scores": scores,
                "overall_score": overall_score,
                "recommendation": self._generate_recommendation(prop, scores, user_profile)
            })
        
        # Rank properties
        analysis_results.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return {
            "ranked_properties": analysis_results,
            "summary": self._generate_decision_summary(analysis_results, user_profile),
            "risk_assessment": self._assess_financial_risk(analysis_results[0]["property"], user_profile),
            "next_steps": self._suggest_next_steps(analysis_results[0]["property"], user_profile)
        }
    
    def _calculate_factor_scores(self, prop: PropertyOption, 
                               user_profile: Dict[str, Any]) -> Dict[DecisionFactor, float]:
        """Calculate scores for each decision factor"""
        
        scores = {}
        
        # Affordability Score (0-10)
        monthly_income = user_profile.get('gross_monthly_income', 5000)
        affordability_ratio = prop.monthly_repayment / monthly_income
        
        if affordability_ratio <= 0.25:
            affordability_score = 10
        elif affordability_ratio <= 0.30:
            affordability_score = 8
        elif affordability_ratio <= 0.35:
            affordability_score = 6
        elif affordability_ratio <= 0.40:
            affordability_score = 4
        else:
            affordability_score = 2
        
        scores[DecisionFactor.AFFORDABILITY] = affordability_score
        
        # Location Convenience Score (0-10)
        mrt_score = max(0, 10 - (prop.mrt_distance_m / 100))  # Closer = better
        location_score = (mrt_score + prop.amenities_score) / 2
        scores[DecisionFactor.LOCATION_CONVENIENCE] = min(10, location_score)
        
        # Investment Potential Score (0-10)
        # Consider age, location, type
        age_penalty = max(0, prop.age / 10)  # Penalty for older properties
        investment_score = prop.resale_potential - age_penalty
        scores[DecisionFactor.INVESTMENT_POTENTIAL] = max(0, min(10, investment_score))
        
        # Lifestyle Fit Score (0-10)
        # Based on user preferences matching
        lifestyle_score = 5  # Base score
        
        # Bonus for matching room count
        preferred_rooms = user_profile.get('room_count', '3-room')
        if prop.rooms == preferred_rooms:
            lifestyle_score += 2
        
        # Bonus for amenities match
        user_amenities = user_profile.get('must_have_amenities', [])
        if len(user_amenities) > 0:
            lifestyle_score += min(3, prop.amenities_score / 3)
        
        scores[DecisionFactor.LIFESTYLE_FIT] = min(10, lifestyle_score)
        
        # Grant Eligibility Score (0-10)
        total_grants = sum(grant.get('amount', 0) for grant in prop.available_grants)
        grant_score = min(10, total_grants / 10000)  # Scale grant amounts
        scores[DecisionFactor.GRANT_ELIGIBILITY] = grant_score
        
        # Timing Score (0-10) - simplified
        scores[DecisionFactor.TIMING] = 7  # Assume neutral timing
        
        return scores
    
    def _calculate_weighted_score(self, scores: Dict[DecisionFactor, float]) -> float:
        """Calculate weighted overall score"""
        total_score = 0
        for factor, score in scores.items():
            weight = self.factor_weights.get(factor, 0)
            total_score += score * weight
        
        return round(total_score, 2)
    
    def _generate_recommendation(self, prop: PropertyOption, 
                               scores: Dict[DecisionFactor, float],
                               user_profile: Dict[str, Any]) -> str:
        """Generate textual recommendation"""
        
        strengths = []
        concerns = []
        
        for factor, score in scores.items():
            if score >= 8:
                strengths.append(factor.value.replace('_', ' ').title())
            elif score <= 4:
                concerns.append(factor.value.replace('_', ' ').title())
        
        recommendation = f"**{prop.address}**\n"
        
        if strengths:
            recommendation += f"**Strengths:** {', '.join(strengths)}\n"
        
        if concerns:
            recommendation += f"**Areas of Concern:** {', '.join(concerns)}\n"
        
        # Specific advice
        affordability_ratio = prop.monthly_repayment / user_profile.get('gross_monthly_income', 5000)
        if affordability_ratio > 0.35:
            recommendation += "⚠️ **High affordability ratio - consider your long-term financial stability**\n"
        
        if prop.mrt_distance_m > 800:
            recommendation += "🚇 **Consider transportation costs and convenience**\n"
        
        if len(prop.available_grants) > 0:
            total_grants = sum(g.get('amount', 0) for g in prop.available_grants)
            recommendation += f"💰 **Available grants: ${total_grants:,.0f}**\n"
        
        return recommendation
    
    def _generate_decision_summary(self, results: List[Dict], 
                                 user_profile: Dict[str, Any]) -> str:
        """Generate overall decision summary"""
        
        if not results:
            return "No properties to analyze."
        
        top_choice = results[0]
        
        summary = f"""
        ## Housing Decision Analysis Summary
        
        **Top Recommendation:** {top_choice['property'].address}
        **Overall Score:** {top_choice['overall_score']}/10
        
        **Key Decision Factors:**
        """
        
        # Sort factors by score for top property
        sorted_factors = sorted(
            top_choice['factor_scores'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for factor, score in sorted_factors:
            factor_name = factor.value.replace('_', ' ').title()
            summary += f"\n- {factor_name}: {score:.1f}/10"
        
        # Financial summary
        monthly_income = user_profile.get('gross_monthly_income', 5000)
        affordability_ratio = top_choice['property'].monthly_repayment / monthly_income
        
        summary += f"""
        
        **Financial Overview:**
        - Monthly Repayment: ${top_choice['property'].monthly_repayment:,.0f}
        - Affordability Ratio: {affordability_ratio:.1%}
        - Total Available Grants: ${sum(g.get('amount', 0) for g in top_choice['property'].available_grants):,.0f}
        """
        
        return summary
    
    def _assess_financial_risk(self, prop: PropertyOption, 
                              user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Assess financial risk of the property purchase"""
        
        monthly_income = user_profile.get('gross_monthly_income', 5000)
        affordability_ratio = prop.monthly_repayment / monthly_income
        
        risk_level = "Low"
        risk_factors = []
        
        if affordability_ratio > 0.35:
            risk_level = "High"
            risk_factors.append("High debt-to-income ratio")
        elif affordability_ratio > 0.30:
            risk_level = "Medium"
            risk_factors.append("Moderate debt-to-income ratio")
        
        if prop.age > 30:
            risk_factors.append("Older property with higher maintenance costs")
        
        if prop.property_type == "HDB" and prop.age > 60:
            risk_factors.append("Limited remaining lease years")
        
        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "affordability_ratio": affordability_ratio,
            "recommended_emergency_fund": prop.monthly_repayment * 6
        }
    
    def _suggest_next_steps(self, prop: PropertyOption, 
                           user_profile: Dict[str, Any]) -> List[str]:
        """Suggest concrete next steps"""
        
        steps = []
        
        # Grant applications
        if prop.available_grants:
            steps.append("Apply for eligible housing grants to reduce purchase cost")
        
        # HDB-specific steps
        if prop.property_type == "HDB":
            steps.append("Check HDB eligibility and application procedures")
            steps.append("Prepare required documents for HDB application")
        
        # Financial preparation
        steps.append("Get pre-approved for housing loan to confirm budget")
        steps.append("Arrange for property valuation")
        
        # Due diligence
        steps.append("Schedule property viewing and inspection")
        steps.append("Research the neighbourhood and amenities")
        
        # Professional consultation
        monthly_income = user_profile.get('gross_monthly_income', 5000)
        if prop.monthly_repayment / monthly_income > 0.30:
            steps.append("Consult with a financial advisor on affordability")
        
        return steps

# Integration tool for agents
#@tool this is supposed to be uncommented but it causes issues with the current setup
def analyze_housing_decision(properties_data: List[Dict], user_profile: Dict) -> str:
    """Analyze housing options and provide decision support"""
    
    try:
        # Convert dict data to PropertyOption objects
        properties = []
        for prop_data in properties_data:
            prop = PropertyOption(
                property_id=prop_data.get('id', ''),
                address=prop_data.get('address', ''),
                price=float(prop_data.get('price', 0)),
                property_type=prop_data.get('type', 'HDB'),
                size_sqft=int(prop_data.get('size', 1000)),
                rooms=prop_data.get('rooms', '3-room'),
                age=int(prop_data.get('age', 10)),
                mrt_distance_m=int(prop_data.get('mrt_distance', 500)),
                school_rating=float(prop_data.get('school_rating', 7)),
                amenities_score=float(prop_data.get('amenities_score', 7)),
                resale_potential=float(prop_data.get('resale_potential', 7)),
                available_grants=prop_data.get('grants', []),
                monthly_repayment=float(prop_data.get('monthly_repayment', 2000)),
                total_cost_including_grants=float(prop_data.get('total_cost', 0))
            )
            properties.append(prop)
        
        engine = DecisionSupportEngine()
        analysis = engine.analyze_options(properties, user_profile)
        
        return analysis['summary'] + "\n\n" + analysis['next_steps'][0] if analysis.get('next_steps') else analysis['summary']
    
    except Exception as e:
        return f"Error in decision analysis: {str(e)}"