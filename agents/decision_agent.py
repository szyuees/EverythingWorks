# agents/decision_agent.py - Fixed import dependencies for new repo structure
from strands import Agent, tool
import json
import logging

logger = logging.getLogger(__name__)

# Import consolidated tools with fallbacks
CONSOLIDATED_TOOLS_AVAILABLE = False
DECISION_ENGINE_AVAILABLE = False

try:
    from tools_consolidated.financial import calculate_affordability
    CONSOLIDATED_TOOLS_AVAILABLE = True
except ImportError:
    calculate_affordability = None
    CONSOLIDATED_TOOLS_AVAILABLE = False

try:
    from core.decision_support_engine import DecisionSupportEngine, PropertyOption
    DECISION_ENGINE_AVAILABLE = True
except ImportError:
    logger.warning("Decision support engine not available")
    DecisionSupportEngine = None
    PropertyOption = None
    DECISION_ENGINE_AVAILABLE = False

@tool
def analyze_property_options(properties_data: str, user_profile_data: str) -> str:
    """
    Analyze property options using the decision support engine
    
    Args:
        properties_data: JSON string of property listings
        user_profile_data: JSON string of user profile information
    """
    try:
        if not DECISION_ENGINE_AVAILABLE:
            return "Decision support engine not available. Please install required dependencies and ensure core.decision_support_engine is accessible."
        
        # Parse input data
        properties = json.loads(properties_data) if isinstance(properties_data, str) else properties_data
        user_profile = json.loads(user_profile_data) if isinstance(user_profile_data, str) else user_profile_data
        
        # Convert to PropertyOption objects
        property_options = []
        for prop_data in properties:
            try:
                prop = PropertyOption(
                    property_id=prop_data.get('id', str(len(property_options))),
                    address=prop_data.get('name', 'Unknown Address'),
                    price=float(prop_data.get('price', 0)),
                    property_type=prop_data.get('type', 'HDB'),
                    size_sqft=int(prop_data.get('size_sqft', 1000)),
                    rooms=str(prop_data.get('rooms', '3-room')),
                    age=int(prop_data.get('age', 10)),
                    mrt_distance_m=int(prop_data.get('mrt_distance', 500)),
                    school_rating=float(prop_data.get('school_rating', 7.0)),
                    amenities_score=float(prop_data.get('amenities_score', 7.0)),
                    resale_potential=float(prop_data.get('resale_potential', 7.0)),
                    available_grants=prop_data.get('grants', []),
                    monthly_repayment=float(prop_data.get('monthly_repayment', prop_data.get('price', 0) * 0.004)),
                    total_cost_including_grants=float(prop_data.get('total_cost', prop_data.get('price', 0)))
                )
                property_options.append(prop)
            except Exception as e:
                logger.warning(f"Skipping invalid property data: {e}")
                continue
        
        if not property_options:
            return "No valid property data provided for analysis"
        
        # Run decision analysis
        engine = DecisionSupportEngine()
        analysis = engine.analyze_options(property_options, user_profile)
        
        # Format response
        response = analysis.get('summary', 'No analysis available')
        
        # Add risk assessment
        risk_info = analysis.get('risk_assessment', {})
        if risk_info:
            risk_level = risk_info.get('risk_level', 'Unknown')
            response += f"\n\n**Risk Assessment:** {risk_level} Risk"
            
            risk_factors = risk_info.get('risk_factors', [])
            if risk_factors:
                response += f"\n**Risk Factors:** {', '.join(risk_factors)}"
        
        # Add next steps
        next_steps = analysis.get('next_steps', [])
        if next_steps:
            response += f"\n\n**Recommended Next Steps:**\n"
            for i, step in enumerate(next_steps[:5], 1):
                response += f"{i}. {step}\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Decision analysis error: {e}")
        return f"Error in decision analysis: {str(e)}"

@tool
def simple_property_comparison(properties_data: str, user_budget: float) -> str:
    """
    Simple property comparison when decision engine is not available
    
    Args:
        properties_data: JSON string of property listings
        user_budget: User's budget as a number
    """
    try:
        properties = json.loads(properties_data) if isinstance(properties_data, str) else properties_data
        
        if not isinstance(properties, list) or not properties:
            return "No properties provided for comparison"
        
        # Simple scoring based on price and basic criteria
        scored_properties = []
        
        for prop in properties:
            if not isinstance(prop, dict):
                continue
                
            price = float(prop.get('price', 0))
            if price <= 0:
                continue
                
            # Simple scoring
            score = 0
            
            # Budget fit (0-10)
            if price <= user_budget:
                score += 10 * (1 - (price / user_budget))
            else:
                score -= 5  # Penalty for over budget
            
            # Add basic bonuses
            if prop.get('location'):
                score += 2
            if prop.get('url'):
                score += 1
            if prop.get('rooms', 0) >= 3:
                score += 1
                
            scored_properties.append({
                'property': prop,
                'score': score,
                'budget_fit': 'Within budget' if price <= user_budget else 'Over budget'
            })
        
        # Sort by score
        scored_properties.sort(key=lambda x: x['score'], reverse=True)
        
        # Format response
        response = f"**Simple Property Comparison (Budget: ${user_budget:,.0f})**\n\n"
        
        for i, item in enumerate(scored_properties[:3], 1):
            prop = item['property']
            response += f"**{i}. {prop.get('name', 'Property')}**\n"
            response += f"   Price: ${prop.get('price', 0):,.0f} ({item['budget_fit']})\n"
            response += f"   Location: {prop.get('location', 'N/A')}\n"
            response += f"   Score: {item['score']:.1f}/10\n\n"
        
        return response
        
    except Exception as e:
        return f"Error in property comparison: {str(e)}"

decision_agent = Agent(
    system_prompt=f"""
    You are a Decision Support Agent that helps users analyze and compare property options.
    
    **System Status**: 
    - Decision Engine: {'Available' if DECISION_ENGINE_AVAILABLE else 'Not Available (using simple comparison)'}
    - Financial Tools: {'Available' if CONSOLIDATED_TOOLS_AVAILABLE else 'Not Available'}
    
    Your role is to:
    1. Analyze multiple property options comprehensively
    2. Score properties based on multiple factors (affordability, location, investment potential)
    3. Provide risk assessment for property purchases
    4. Recommend next steps for property acquisition
    
    **Analysis Factors:**
    - Affordability (debt-to-income ratios, monthly payments)
    - Location convenience (MRT access, amenities)
    - Investment potential (resale value, area development)
    - Lifestyle fit (user preferences matching)
    - Grant eligibility (available subsidies)
    - Market timing considerations
    
    **Decision Framework:**
    - Weight factors based on user priorities
    - Consider Singapore-specific regulations (TDSR, CPF usage)
    - Account for long-term financial implications
    - Factor in market conditions and trends
    
    **Tool Usage:**
    {'- Use analyze_property_options for comprehensive analysis when decision engine is available' if DECISION_ENGINE_AVAILABLE else '- Use simple_property_comparison for basic analysis (decision engine not available)'}
    - Always consider user budget constraints
    - Provide clear reasoning for recommendations
    
    Always provide balanced, objective analysis with clear reasoning for recommendations.
    Include both quantitative scores and qualitative insights.
    """,
    tools=[
        analyze_property_options if DECISION_ENGINE_AVAILABLE else simple_property_comparison,
        calculate_affordability if CONSOLIDATED_TOOLS_AVAILABLE else None
    ]
)