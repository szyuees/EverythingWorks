# page.py - Fixed import dependencies for new repo structure
from dotenv import load_dotenv
load_dotenv()

import os
import gradio as gr
import logging
from datetime import datetime
import json

os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'

# Enhanced logging
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Starting Enhanced Housing Assistant with Consolidated Tools")

# Import consolidated tools and check availability
CONSOLIDATED_TOOLS_AVAILABLE = False
MCP_AVAILABLE = False

try:
    from tools_consolidated import get_tool_status, get_system_status
    CONSOLIDATED_TOOLS_AVAILABLE = True
    logger.info("Consolidated tools loaded successfully")
    
    # Log tool status
    try:
        status = get_tool_status()
        available_tools = status['available_tools']
        total_tools = status['total_tools'] 
        logger.info(f"Tool Status: {available_tools}/{total_tools} tools available")
    except Exception as e:
        logger.warning(f"Could not get tool status: {e}")
    
except ImportError as e:
    logger.warning(f"Consolidated tools not available: {e}")

# Import orchestrator agent
try:
    from agents.orchestrator_agent import orchestrator
    logger.info("Orchestrator agent loaded")
except ImportError as e:
    logger.error(f"Failed to load orchestrator agent: {e}")
    # Create a minimal fallback orchestrator
    class FallbackOrchestrator:
        def __call__(self, query):
            return f"System error: Orchestrator not available. Error: {str(e)}"
    orchestrator = FallbackOrchestrator()

# Import context manager
try:
    from core.mcp_context_manager import MCPContextManager
    MCP_AVAILABLE = True
    logger.info("MCP Context Manager available")
except ImportError as e:
    logger.warning(f"MCP Context Manager not available: {e}")
    MCPContextManager = None

class EnhancedChatbotWithContext:
    def __init__(self, agent, context_manager=None):
        self.agent = agent
        self.context_manager = context_manager
        self.history = []
        self.user_sessions = {}
    
    def ask(self, user_message: str, user_id: str = "default_user"):
        """Enhanced ask with context management and consolidated tools"""
        
        try:
            # Get user context if MCP is available
            context_prompt = ""
            if self.context_manager:
                try:
                    user_context = self.context_manager.get_user_context(user_id)
                    context_prompt = self._build_context_prompt(user_context)
                    
                    # Extract and update profile from message
                    self._extract_profile_updates(user_id, user_message)
                    
                except Exception as e:
                    logger.warning(f"Context management error: {e}")
            
            # Build conversation with context
            self.history.append(("user", user_message))
            
            conversation = context_prompt + "\n\n" if context_prompt else ""
            for role, msg in self.history[-3:]:  # Keep last 3 exchanges
                conversation += f"{role.upper()}: {msg}\n"
            
            # Call agent and ensure string response
            agent_response = self.agent(conversation)
            
            # Handle AgentResult objects properly
            if hasattr(agent_response, 'content'):
                response = str(agent_response.content)
            elif hasattr(agent_response, 'text'):
                response = str(agent_response.text)
            else:
                response = str(agent_response)
            
            self.history.append(("assistant", response))
            
            # Enhance response formatting
            enhanced_response = self._enhance_response(response, user_id)
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Error in ask method: {e}")
            return f"I encountered an error processing your request: {str(e)}. Please try again."
    
    def _build_context_prompt(self, user_context):
        """Build context prompt for agent"""
        try:
            if not isinstance(user_context, dict):
                return ""
                
            profile = user_context.get('profile', {})
            completion = user_context.get('completion_score', 0)
            
            context_items = []
            if profile.get('citizenship_status'):
                context_items.append(f"Citizenship: {profile['citizenship_status']}")
            if profile.get('gross_monthly_income'):
                context_items.append(f"Income: ${profile['gross_monthly_income']:,.0f}")
            if profile.get('preferred_locations'):
                locations = profile['preferred_locations']
                if isinstance(locations, list):
                    context_items.append(f"Preferred areas: {', '.join(locations)}")
            
            if context_items:
                return f"USER CONTEXT - Profile completion: {completion:.0%} | " + " | ".join(context_items)
            return ""
        except Exception as e:
            logger.warning(f"Error building context prompt: {e}")
            return ""
    
    def _extract_profile_updates(self, user_id, message):
        """Extract and update profile from message"""
        if not self.context_manager:
            return
        
        try:
            message_lower = message.lower()
            updates = {}
            
            # FIXED: Enhanced citizenship extraction
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
                    current_areas = self.context_manager.user_profiles[user_id].preferred_locations or []
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
            
            # Extract budget information
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
                self.context_manager.update_user_profile(user_id, **updates)
                logger.info(f"Updated profile for {user_id}: {updates}")
                
        except Exception as e:
            logger.warning(f"Error extracting profile updates: {e}")
    
    def _enhance_response(self, response, user_id):
        """Enhance response with context-aware elements"""
        if not self.context_manager or not response:
            return response
        
        try:
            context = self.context_manager.get_user_context(user_id)
            if not isinstance(context, dict):
                return response
                
            completion = context.get('completion_score', 0)
            
            # Add profile completion indicator for low completion scores
            if completion < 0.8:
                missing_info = []
                profile = context.get('profile', {})
                
                if not profile.get('citizenship_status'):
                    missing_info.append('citizenship status')
                if not profile.get('gross_monthly_income'):
                    missing_info.append('income level')
                if not profile.get('preferred_locations'):
                    missing_info.append('preferred locations')
                
                if missing_info:
                    completion_note = f"\n\n**To provide better recommendations**: Share your {', '.join(missing_info[:2])}"
                    response = str(response) + completion_note
            
            return response
            
        except Exception as e:
            logger.warning(f"Response enhancement error: {e}")
            return response

class BasicChatbot:
    """Fallback chatbot if enhanced features fail"""
    def __init__(self, agent):
        self.agent = agent
        self.history = []
    
    def ask(self, user_message: str, user_id: str = "default_user"):
        try:
            self.history.append(("user", user_message))
            
            conversation = ""
            for role, msg in self.history[-5:]:  # Keep last 5 exchanges
                conversation += f"{role.upper()}: {msg}\n"
            
            # Call agent and ensure string response
            agent_response = self.agent(conversation)
            
            # Handle AgentResult objects properly
            if hasattr(agent_response, 'content'):
                response = str(agent_response.content)
            elif hasattr(agent_response, 'text'):
                response = str(agent_response.text)
            else:
                response = str(agent_response)
            
            self.history.append(("assistant", response))
            return response
            
        except Exception as e:
            logger.error(f"Error in basic chatbot: {e}")
            return f"I encountered an error: {str(e)}. Please try rephrasing your question."

# Initialize systems with comprehensive error handling
try:
    # Initialize MCP Context Manager if available
    if MCP_AVAILABLE:
        context_manager = MCPContextManager()
        logger.info("MCP Context Manager initialized")
        
        # Initialize the enhanced chatbot
        chatbot = EnhancedChatbotWithContext(orchestrator, context_manager)
        logger.info("Enhanced chatbot with context management initialized")
    else:
        context_manager = None
        chatbot = BasicChatbot(orchestrator)
        logger.info("Basic chatbot initialized (MCP unavailable)")

except Exception as e:
    logger.error(f"System initialization error: {e}")
    context_manager = None
    chatbot = BasicChatbot(orchestrator)
    logger.info("Fallback: Basic chatbot initialized")

def chat_with_enhanced_housing_bot(user_input, session_state):
    """Enhanced chat function with session management"""
    
    if not user_input or not user_input.strip():
        return "", session_state
    
    # Create session ID if new
    if not session_state:
        session_state = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    logger.info(f"Session {session_state}: {user_input}")
    
    try:
        response = chatbot.ask(user_input, user_id=session_state)
        
        # Ensure response is a string
        if not isinstance(response, str):
            response = str(response)
        
        logger.info(f"Session {session_state} Response: {response[:100]}...")
        return response, session_state
        
    except Exception as e:
        logger.error(f"Session {session_state} Error: {e}")
        error_response = f"I encountered an error: {str(e)}\n\nPlease try rephrasing your question or contact support if the issue persists."
        return error_response, session_state

# Create enhanced interface
with gr.Blocks(
    title="Enhanced Singapore Housing Assistant",
    theme=gr.themes.Soft(primary_hue="indigo", secondary_hue="blue")
) as iface:
    
    # Header with system status
    system_status = "Consolidated Tools" if CONSOLIDATED_TOOLS_AVAILABLE else "Legacy Mode"
    mcp_status = "Context Management" if MCP_AVAILABLE else "Basic Mode"
    
    gr.HTML(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4f46e5, #3b82f6); color: white; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 2em;">Enhanced Singapore Housing Assistant</h1>
        <p style="font-size: 18px; margin: 5px 0 0;">AI-powered housing guidance with personalized recommendations</p>
        <p style="font-size: 14px; margin: 5px 0 0; opacity: 0.8;">Status: {system_status} | {mcp_status}</p>
    </div>
    """)
    initial_history = [
        {"role": "assistant", "content": "Hi! I am a housing chatbot here to answer any housing-related queries you might have.🤩"}
    ]
    with gr.Row():
        # Main conversation area
        with gr.Column(scale=3):
            chatbot_interface = gr.Chatbot(
                type="messages",
                label="Chat with Housing Assistant",
                height=500,
                show_label=True,
                value = initial_history
            )
            
            user_input = gr.Textbox(
                placeholder="Ask about housing grants, property search, eligibility requirements, or any housing-related questions...",
                lines=3,
                show_label=False
            )
            
            with gr.Row():
                submit_btn = gr.Button("Send Message", variant="primary", size="lg")
                clear_btn = gr.Button("New Conversation", variant="secondary")
        
        # Sidebar
        with gr.Column(scale=1):
            gr.Markdown("### Quick Start")
            
            sample_queries = [
                "What housing grants am I eligible for as a Singapore citizen?",
                "I earn $6000/month, what's my housing budget?",
                "Can you provide a list of flats that are suitable for me?"
            ]
            
            sample_buttons = []
            for i, query in enumerate(sample_queries):
                btn = gr.Button(query, size="sm")
                sample_buttons.append(btn)
            
            gr.Markdown("### Sources From")
            gr.Markdown("""
            - HDB.sg
            - PropertyGuru
            - 99.co
            - Propnex
            - SRX
            - CPF
            """)

            # 👇 Add Tech Stack section here
            gr.Markdown("### Tech Stack")
            gr.Markdown("""
            - **Frontend**: Gradio  
            - **Backend**: Python  
            - **Tools**: RAG Pipeline, MCP Pipeline 
            - **Hosting**: AWS
            """)
    
    # Session state
    session_state = gr.State()
    
    def process_chat(message, history, session_id):
        """Process chat with proper error handling"""
        if not message or not message.strip():
            return history, "", session_id
        
        try:
            history = history or []
            history.append({'role': 'user', 'content': message})
            
            response, new_session_id = chat_with_enhanced_housing_bot(message, session_id)
            history.append({'role': 'assistant', 'content': response})
            
            return history, "", new_session_id
        except Exception as e:
            logger.error(f"Error in process_chat: {e}")
            if history:
                history.append({'role': 'assistant', 'content': f"Error processing message: {str(e)}"})
            return history, "", session_id
    
    # Event handlers
    submit_btn.click(
        process_chat,
        inputs=[user_input, chatbot_interface, session_state],
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    user_input.submit(
        process_chat,
        inputs=[user_input, chatbot_interface, session_state],
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    clear_btn.click(
        lambda: (
        [{"role": "assistant", "content": "Hi! I am a housing chatbot here to answer any housing-related queries you might have 🤩."}],
        "", 
        None
        ),
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    # Sample button handlers
    for btn, query in zip(sample_buttons, sample_queries):
        btn.click(
            lambda q=query: q,
            outputs=user_input
        )

if __name__ == "__main__":
    logger.info("Launching Enhanced Singapore Housing Assistant")
    system_features = []
    if CONSOLIDATED_TOOLS_AVAILABLE:
        system_features.append("Consolidated Tools")
    if MCP_AVAILABLE:
        system_features.append("Context Management")
    
    logger.info(f"Active Features: {', '.join(system_features) if system_features else 'Basic Mode'}")
    
    try:
        iface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True,
            quiet=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Cleaning up resources...")
        try:
            if 'iface' in locals():
                iface.close()
        except:
            pass