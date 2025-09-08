# mcp_context_manager.py
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from aws_session import session

logger = logging.getLogger(__name__)

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
    budget_range: Optional[Tuple[float, float]] = None
    
    # Housing Preferences
    preferred_locations: Optional[List[str]] = None
    flat_type: Optional[str] = None
    room_count: Optional[str] = None
    must_have_amenities: Optional[List[str]] = None
    
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
    """Manages user context throughout the housing journey with comprehensive error handling"""
    
    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.session_history: Dict[str, List[Dict]] = {}
        logger.info("MCPContextManager initialized")
    
    def create_user_session(self, user_id: str) -> str:
        """Create a new user session with error handling"""
        try:
            if user_id not in self.user_profiles:
                self.user_profiles[user_id] = UserProfile()
                self.session_history[user_id] = []
                logger.info(f"Created new user session: {user_id}")
            return user_id
        except Exception as e:
            logger.error(f"Error creating user session {user_id}: {e}")
            return user_id
    
    def update_user_profile(self, user_id: str, **kwargs) -> UserProfile:
        """Update user profile with new information and error handling"""
        try:
            if user_id not in self.user_profiles:
                self.create_user_session(user_id)
            
            profile = self.user_profiles[user_id]
            updated_fields = []
            
            for key, value in kwargs.items():
                if hasattr(profile, key):
                    old_value = getattr(profile, key)
                    setattr(profile, key, value)
                    if old_value != value:
                        updated_fields.append(key)
                else:
                    logger.warning(f"Unknown profile field: {key}")
            
            if updated_fields:
                logger.info(f"Updated profile {user_id}: {updated_fields}")
                self._log_interaction(user_id, 'profile_update', {'fields': updated_fields})
            
            return profile
            
        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {e}")
            # Return existing profile or create new one
            if user_id in self.user_profiles:
                return self.user_profiles[user_id]
            else:
                self.user_profiles[user_id] = UserProfile()
                return self.user_profiles[user_id]
    
    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context with error handling"""
        try:
            if user_id not in self.user_profiles:
                self.create_user_session(user_id)
            
            profile = self.user_profiles[user_id]
            recent_interactions = self.session_history.get(user_id, [])[-5:]  # Last 5 interactions
            
            return {
                'profile': asdict(profile),
                'journey_stage': profile.journey_stage.value,
                'recent_interactions': recent_interactions,
                'completion_score': self._calculate_profile_completion(profile)
            }
            
        except Exception as e:
            logger.error(f"Error getting user context {user_id}: {e}")
            # Return minimal context
            return {
                'profile': {},
                'journey_stage': UserJourneyStage.INITIAL_INQUIRY.value,
                'recent_interactions': [],
                'completion_score': 0.0
            }
    
    def advance_journey_stage(self, user_id: str, new_stage: UserJourneyStage):
        """Advance user to next stage in housing journey with validation"""
        try:
            if user_id not in self.user_profiles:
                self.create_user_session(user_id)
            
            old_stage = self.user_profiles[user_id].journey_stage
            self.user_profiles[user_id].journey_stage = new_stage
            
            self._log_interaction(user_id, 'stage_advancement', {
                'old_stage': old_stage.value,
                'new_stage': new_stage.value
            })
            
            logger.info(f"Advanced user {user_id} from {old_stage.value} to {new_stage.value}")
            
        except Exception as e:
            logger.error(f"Error advancing journey stage for {user_id}: {e}")
    
    def _calculate_profile_completion(self, profile: UserProfile) -> float:
        """Calculate how complete the user profile is"""
        try:
            essential_fields = [
                'citizenship_status', 'age', 'marital_status', 'gross_monthly_income',
                'budget_range', 'preferred_locations', 'flat_type', 'first_time_buyer'
            ]
            
            completed = 0
            for field in essential_fields:
                value = getattr(profile, field)
                if value is not None and value != [] and value != "":
                    if isinstance(value, list) and len(value) > 0:
                        completed += 1
                    elif not isinstance(value, list):
                        completed += 1
            
            return completed / len(essential_fields)
            
        except Exception as e:
            logger.error(f"Error calculating profile completion: {e}")
            return 0.0
    
    def _log_interaction(self, user_id: str, action: str, data: Dict[str, Any]):
        """Log user interactions for context with error handling"""
        try:
            interaction = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'data': data
            }
            
            if user_id not in self.session_history:
                self.session_history[user_id] = []
            
            self.session_history[user_id].append(interaction)
            
            # Keep only last 20 interactions to prevent memory issues
            if len(self.session_history[user_id]) > 20:
                self.session_history[user_id] = self.session_history[user_id][-20:]
                
        except Exception as e:
            logger.error(f"Error logging interaction for {user_id}: {e}")
    
    def _extract_profile_updates(self, user_id, message):
        """Extract profile information from user message"""
        # CRITICAL BUG FIX: Remove the incorrect self.context_manager check
        # The original code had: if not self.context_manager: return
        # This was wrong because self.context_manager doesn't exist in this class
        
        try:
            message_lower = message.lower()
            updates = {}
            
            # Enhanced citizenship extraction - FIXED
            if any(term in message_lower for term in ['singaporean', 'singapore citizen', 'citizen of singapore']):
                updates['citizenship_status'] = 'Singapore Citizen'
            elif 'citizen' in message_lower and 'singapore' in message_lower:
                updates['citizenship_status'] = 'Singapore Citizen'
            elif any(term in message_lower for term in ['pr', 'permanent resident', 'perm resident']):
                updates['citizenship_status'] = 'Permanent Resident'
            elif any(term in message_lower for term in ['foreigner', 'foreign', 'work permit', 'employment pass']):
                updates['citizenship_status'] = 'Foreigner'
            
            # Enhanced income extraction with better patterns
            import re
            income_patterns = [
                r'\$\s*(\d{1,2}[,\s]*\d{3,})',  # $6000, $6,000
                r'(\d{1,2}[,\s]*\d{3,})\s*(?:dollars?|sgd|per month|monthly)',  # 6000 dollars
                r'earn(?:ing)?\s+\$?(\d{1,2}[,\s]*\d{3,})',  # earning $6000
                r'income\s+(?:of\s+)?\$?(\d{1,2}[,\s]*\d{3,})',  # income of $6000
                r'(\d{1,2})k\s*(?:per month|monthly|income)',  # 6k per month
            ]
            
            for pattern in income_patterns:
                income_match = re.search(pattern, message_lower)
                if income_match:
                    try:
                        income_str = income_match.group(1).replace(',', '').replace(' ', '')
                        if 'k' in message_lower and income_match:
                            # Handle "6k" format
                            k_match = re.search(r'(\d+)k', message_lower)
                            if k_match:
                                income = float(k_match.group(1)) * 1000
                        else:
                            income = float(income_str)
                        
                        if 1000 <= income <= 50000:  # Reasonable income range
                            updates['gross_monthly_income'] = income
                            break
                    except (ValueError, AttributeError):
                        continue
            
            # Extract locations (Singapore areas)
            sg_areas = ['tampines', 'jurong', 'woodlands', 'punggol', 'sengkang', 'bishan', 'toa payoh', 
                       'bedok', 'hougang', 'ang mo kio', 'clementi', 'bukit batok', 'yishun']
            mentioned_areas = [area for area in sg_areas if area in message_lower]
            if mentioned_areas:
                try:
                    # FIXED: Use self instead of self.context_manager
                    current_areas = self.user_profiles[user_id].preferred_locations or []
                    updates['preferred_locations'] = list(set(current_areas + mentioned_areas))
                except (KeyError, AttributeError):
                    updates['preferred_locations'] = mentioned_areas
            
            # Extract property type and room count
            if any(term in message_lower for term in ['hdb', 'public housing']):
                updates['flat_type'] = 'HDB'
            elif any(term in message_lower for term in ['private', 'condo', 'condominium']):
                updates['flat_type'] = 'Private'
            elif any(term in message_lower for term in ['ec', 'executive condo']):
                updates['flat_type'] = 'EC'
            
            # Extract room count
            room_patterns = [
                r'(\d+)[-\s]?room',
                r'(\d+)[-\s]?bed'
            ]
            for pattern in room_patterns:
                room_match = re.search(pattern, message_lower)
                if room_match:
                    room_count = room_match.group(1)
                    updates['room_count'] = f"{room_count}-room"
                    break
            
            # Extract budget information - NEW
            budget_patterns = [
                r'under\s+\$?(\d{3,}k?)',  # under $800k
                r'below\s+\$?(\d{3,}k?)',  # below $800k
                r'less than\s+\$?(\d{3,}k?)',  # less than $800k
                r'budget\s+(?:of\s+)?\$?(\d{3,}k?)',  # budget of $800k
            ]
            
            for pattern in budget_patterns:
                budget_match = re.search(pattern, message_lower)
                if budget_match:
                    try:
                        budget_str = budget_match.group(1)
                        if 'k' in budget_str:
                            budget = float(budget_str.replace('k', '')) * 1000
                        else:
                            budget = float(budget_str)
                        
                        if budget > 100000:  # Reasonable property budget
                            updates['budget_range'] = (budget * 0.8, budget)  # 80% to max
                            break
                    except ValueError:
                        continue
                        
            if updates:
                # FIXED: Use self instead of self.context_manager
                self.update_user_profile(user_id, **updates)
                logger.info(f"Updated profile for {user_id}: {updates}")
                
        except Exception as e:
            logger.warning(f"Error extracting profile updates: {e}")
    
    def get_contextual_prompt(self, user_id: str, agent_type: str) -> str:
        """Generate contextual prompt based on user journey with error handling"""
        try:
            context = self.get_user_context(user_id)
            profile = context.get('profile', {})
            stage = context.get('journey_stage', UserJourneyStage.INITIAL_INQUIRY.value)
            completion = context.get('completion_score', 0.0)
            
            # Build context summary
            context_items = []
            if profile.get('citizenship_status'):
                context_items.append(f"Citizenship: {profile['citizenship_status']}")
            if profile.get('gross_monthly_income'):
                context_items.append(f"Income: ${profile['gross_monthly_income']:,.0f}")
            if profile.get('budget_range') and isinstance(profile['budget_range'], (list, tuple)) and len(profile['budget_range']) == 2:
                context_items.append(f"Budget: ${profile['budget_range'][0]:,.0f} - ${profile['budget_range'][1]:,.0f}")
            if profile.get('preferred_locations'):
                locations = profile['preferred_locations']
                if isinstance(locations, list) and locations:
                    context_items.append(f"Areas: {', '.join(locations[:3])}")
            
            base_prompt = f"""
User Context Summary:
- Journey Stage: {stage}
- Profile Completion: {completion:.0%}
"""
            
            if context_items:
                base_prompt += "- " + " | ".join(context_items) + "\n"
            
            # Stage-specific guidance
            if stage == UserJourneyStage.INITIAL_INQUIRY.value:
                base_prompt += "Focus: Understand user needs and collect essential information efficiently."
            elif stage == UserJourneyStage.PROFILE_COLLECTION.value:
                base_prompt += "Focus: Complete missing profile information before proceeding."
            elif stage == UserJourneyStage.GRANT_ASSESSMENT.value:
                base_prompt += "Focus: Provide comprehensive grant eligibility analysis."
            elif stage == UserJourneyStage.PROPERTY_SEARCH.value:
                base_prompt += "Focus: Find suitable properties matching user criteria."
            elif stage == UserJourneyStage.DECISION_SUPPORT.value:
                base_prompt += "Focus: Help user compare options and make informed decisions."
            elif stage == UserJourneyStage.TRANSACTION_GUIDANCE.value:
                base_prompt += "Focus: Guide user through purchase process and next steps."
            
            return base_prompt
            
        except Exception as e:
            logger.error(f"Error generating contextual prompt for {user_id}: {e}")
            return "User Context: New inquiry - Focus on understanding user needs."
    
    def get_profile_gaps(self, user_id: str) -> List[str]:
        """Identify missing essential profile information"""
        try:
            if user_id not in self.user_profiles:
                return ["All profile information needed"]
            
            profile = self.user_profiles[user_id]
            gaps = []
            
            if not profile.citizenship_status:
                gaps.append("citizenship status")
            if not profile.gross_monthly_income:
                gaps.append("monthly income")
            if not profile.budget_range:
                gaps.append("budget range")
            if not profile.preferred_locations or len(profile.preferred_locations) == 0:
                gaps.append("preferred locations")
            if not profile.flat_type:
                gaps.append("flat type preference")
            if profile.first_time_buyer is None:
                gaps.append("first-time buyer status")
            
            return gaps
            
        except Exception as e:
            logger.error(f"Error identifying profile gaps for {user_id}: {e}")
            return ["Unable to assess profile completeness"]
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export user data for analysis or transfer"""
        try:
            if user_id not in self.user_profiles:
                return {"error": "User not found"}
            
            return {
                "user_id": user_id,
                "profile": asdict(self.user_profiles[user_id]),
                "session_history": self.session_history.get(user_id, []),
                "export_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error exporting user data for {user_id}: {e}")
            return {"error": f"Export failed: {str(e)}"}

# Utility functions for integration
def create_context_manager() -> MCPContextManager:
    """Factory function to create context manager with error handling"""
    try:
        return MCPContextManager()
    except Exception as e:
        logger.error(f"Failed to create context manager: {e}")
        raise

def safe_context_call(context_manager, method_name: str, *args, **kwargs):
    """Safely call context manager methods with error handling"""
    try:
        if context_manager is None:
            return None
        
        method = getattr(context_manager, method_name)
        return method(*args, **kwargs)
        
    except Exception as e:
        logger.error(f"Error calling {method_name}: {e}")
        return None