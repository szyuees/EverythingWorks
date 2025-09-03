# mcp_context_manager.py
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class UserJourneyStage(Enum):
    INITIAL_INQUIRY = "initial_inquiry"
    PROFILE_COLLECTION = "profile_collection"
    GRANT_ASSESSMENT = "grant_assessment"
    PROPERTY_SEARCH = "property_search"
    DECISION_SUPPORT = "decision_support"
    TRANSACTION_GUIDANCE = "transaction_guidance"

@dataclass
class UserProfile:
    """Comprehensive user profile for housing decisions"""
    # Demographics
    citizenship_status: Optional[str] = None
    age: Optional[int] = None
    marital_status: Optional[str] = None
    household_size: Optional[int] = None
    
    # Financial
    gross_monthly_income: Optional[float] = None
    cpf_balance: Optional[float] = None
    budget_range: Optional[tuple] = None
    
    # Housing Preferences
    preferred_locations: List[str] = None
    flat_type: Optional[str] = None
    room_count: Optional[str] = None
    must_have_amenities: List[str] = None
    
    # Context
    first_time_buyer: Optional[bool] = None
    urgency_level: Optional[str] = None
    journey_stage: UserJourneyStage = UserJourneyStage.INITIAL_INQUIRY
    
    def __post_init__(self):
        if self.preferred_locations is None:
            self.preferred_locations = []
        if self.must_have_amenities is None:
            self.must_have_amenities = []

class MCPContextManager:
    """Manages user context throughout the housing journey"""
    
    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.session_history: Dict[str, List[Dict]] = {}
    
    def create_user_session(self, user_id: str) -> str:
        """Create a new user session"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = UserProfile()
            self.session_history[user_id] = []
        return user_id
    
    def update_user_profile(self, user_id: str, **kwargs) -> UserProfile:
        """Update user profile with new information"""
        if user_id not in self.user_profiles:
            self.create_user_session(user_id)
        
        profile = self.user_profiles[user_id]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        return profile
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context"""
        if user_id not in self.user_profiles:
            self.create_user_session(user_id)
        
        profile = self.user_profiles[user_id]
        recent_interactions = self.session_history[user_id][-5:]  # Last 5 interactions
        
        return {
            'profile': asdict(profile),
            'journey_stage': profile.journey_stage.value,
            'recent_interactions': recent_interactions,
            'completion_score': self._calculate_profile_completion(profile)
        }
    
    def advance_journey_stage(self, user_id: str, new_stage: UserJourneyStage):
        """Advance user to next stage in housing journey"""
        if user_id in self.user_profiles:
            self.user_profiles[user_id].journey_stage = new_stage
            self._log_interaction(user_id, 'stage_advancement', {'new_stage': new_stage.value})
    
    def _calculate_profile_completion(self, profile: UserProfile) -> float:
        """Calculate how complete the user profile is"""
        total_fields = 12  # Essential fields for housing decision
        completed = 0
        
        essential_fields = [
            'citizenship_status', 'age', 'marital_status', 'gross_monthly_income',
            'budget_range', 'preferred_locations', 'flat_type', 'first_time_buyer'
        ]
        
        for field in essential_fields:
            value = getattr(profile, field)
            if value is not None and value != [] and value != "":
                completed += 1
        
        return completed / len(essential_fields)
    
    def _log_interaction(self, user_id: str, action: str, data: Dict[str, Any]):
        """Log user interactions for context"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'data': data
        }
        
        if user_id not in self.session_history:
            self.session_history[user_id] = []
        
        self.session_history[user_id].append(interaction)
    
    def get_contextual_prompt(self, user_id: str, agent_type: str) -> str:
        """Generate contextual prompt based on user journey"""
        context = self.get_user_context(user_id)
        profile = context['profile']
        stage = context['journey_stage']
        completion = context['completion_score']
        
        base_prompt = f"""
        User Context Summary:
        - Journey Stage: {stage}
        - Profile Completion: {completion:.0%}
        - Citizenship: {profile.get('citizenship_status', 'Unknown')}
        - Budget Range: {profile.get('budget_range', 'Not specified')}
        - Preferred Areas: {', '.join(profile.get('preferred_locations', []))}
        """
        
        # Stage-specific guidance
        if stage == UserJourneyStage.INITIAL_INQUIRY.value:
            base_prompt += "\nFocus: Understand user needs and collect essential information efficiently."
        elif stage == UserJourneyStage.PROFILE_COLLECTION.value:
            base_prompt += "\nFocus: Complete missing profile information before proceeding."
        elif stage == UserJourneyStage.GRANT_ASSESSMENT.value:
            base_prompt += "\nFocus: Provide comprehensive grant eligibility analysis."
        elif stage == UserJourneyStage.PROPERTY_SEARCH.value:
            base_prompt += "\nFocus: Find suitable properties matching user criteria."
        
        return base_prompt

# Integration with existing chatbot
class EnhancedChatbotWithMCP:
    def __init__(self, agent, context_manager: MCPContextManager):
        self.agent = agent
        self.context_manager = context_manager
        self.history = []
    
    def ask(self, user_message: str, user_id: str = "default_user"):
        """Enhanced ask method with MCP context"""
        # Get user context
        user_context = self.context_manager.get_user_context(user_id)
        
        # Generate contextual prompt
        contextual_prompt = self.context_manager.get_contextual_prompt(user_id, "orchestrator")
        
        # Add context to conversation
        enhanced_message = f"{contextual_prompt}\n\nUser Query: {user_message}"
        
        self.history.append(("user", user_message))
        
        # Build conversation with context
        conversation = contextual_prompt + "\n\n"
        for role, msg in self.history[-3:]:  # Keep last 3 exchanges
            conversation += f"{role.upper()}: {msg}\n"
        
        response = self.agent(conversation)
        self.history.append(("assistant", response))
        
        # Extract any profile updates from the conversation
        self._extract_and_update_profile(user_id, user_message, response)
        
        return response
    
    def _extract_and_update_profile(self, user_id: str, user_msg: str, assistant_response: str):
        """Extract profile information from conversation"""
        # Simple keyword extraction - in production, use NLP
        updates = {}
        
        # Extract citizenship
        if any(word in user_msg.lower() for word in ['citizen', 'pr', 'foreigner']):
            if 'citizen' in user_msg.lower():
                updates['citizenship_status'] = 'Singapore Citizen'
            elif 'pr' in user_msg.lower() or 'permanent resident' in user_msg.lower():
                updates['citizenship_status'] = 'Permanent Resident'
        
        # Extract budget information
        if '$' in user_msg or 'budget' in user_msg.lower():
            # Simple regex to extract budget range
            import re
            amounts = re.findall(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', user_msg)
            if len(amounts) >= 2:
                updates['budget_range'] = (float(amounts[0].replace(',', '')), 
                                        float(amounts[1].replace(',', '')))
        
        # Extract locations
        sg_areas = ['tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan', 'toa payoh']
        mentioned_areas = [area for area in sg_areas if area in user_msg.lower()]
        if mentioned_areas:
            updates['preferred_locations'] = mentioned_areas
        
        if updates:
            self.context_manager.update_user_profile(user_id, **updates)

# Usage in main application
context_manager = MCPContextManager()
enhanced_chatbot = EnhancedChatbotWithMCP(orchestrator, context_manager)