import gradio as gr
from agents.orchestrator_agent import orchestrator
import logging
import boto3
from datetime import datetime
import json
import traceback

# Import new core systems with proper error handling
try:
    from core.mcp_context_manager import MCPContextManager
    MCP_AVAILABLE = True
except ImportError as e:
    logging.warning(f"MCP Context Manager not available: {e}")
    MCPContextManager = None
    MCP_AVAILABLE = False

try:
    from tools import initialize_rag_system
    RAG_AVAILABLE = True
except ImportError as e:
    logging.warning(f"RAG system not available: {e}")
    RAG_AVAILABLE = False

# --- Enhanced Logging ---
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info("Starting Enhanced Housing Assistant")

# Initialize systems with proper error handling
context_manager = None
rag_status = "Not available"

try:
    # Initialize RAG system if available
    if RAG_AVAILABLE:
        rag_status = initialize_rag_system()
        logger.info(f"RAG Status: {rag_status}")
    
    # Initialize MCP Context Manager if available
    if MCP_AVAILABLE:
        context_manager = MCPContextManager()
        logger.info("MCP Context Manager initialized")
    
except Exception as e:
    logger.error(f"Initialization error: {e}")
    logger.error(traceback.format_exc())

class EnhancedChatbotWithContext:
    def __init__(self, agent, context_manager=None):
        self.agent = agent
        self.context_manager = context_manager
        self.history = []
        self.user_sessions = {}
    
    def ask(self, user_message: str, user_id: str = "default_user"):
        """Enhanced ask with context management and proper error handling"""
        
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
            logger.error(traceback.format_exc())
            return f"I encountered an error processing your request: {str(e)}. Please try again."
    
    def _build_context_prompt(self, user_context):
        """Build context prompt for agent with proper error handling"""
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
        """Extract profile information from user message with error handling"""
        if not self.context_manager:
            return
        
        try:
            message_lower = message.lower()
            updates = {}
            
            # Extract citizenship
            if 'citizen' in message_lower:
                updates['citizenship_status'] = 'Singapore Citizen'
            elif 'pr' in message_lower or 'permanent resident' in message_lower:
                updates['citizenship_status'] = 'Permanent Resident'
            
            # Extract income (simple regex)
            import re
            income_match = re.search(r'\$?(\d{1,2},?\d{3,})', message)
            if income_match:
                try:
                    income = int(income_match.group(1).replace(',', ''))
                    if income > 1000:  # Reasonable income threshold
                        updates['gross_monthly_income'] = float(income)
                except ValueError:
                    pass
            
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
            
            # Add profile completion indicator
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
                    completion_note = f"\n\n💡 **To provide better recommendations**: Share your {', '.join(missing_info[:2])}"
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

# Initialize chatbot with fallback
if context_manager:
    chatbot = EnhancedChatbotWithContext(orchestrator, context_manager)
    logger.info("Enhanced chatbot with context management initialized")
else:
    chatbot = BasicChatbot(orchestrator)
    logger.info("Basic chatbot initialized (fallback mode)")

def chat_with_enhanced_housing_bot(user_input, session_state):
    """Enhanced chat function with session management and error handling"""
    
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
        logger.error(traceback.format_exc())
        error_response = f"I encountered an error: {str(e)}\n\nPlease try rephrasing your question or contact support if the issue persists."
        return error_response, session_state
    
'''
# Create enhanced interface with better error handling
with gr.Blocks(title="Enhanced Singapore Housing Assistant", theme=gr.themes.Soft()) as iface:
    
    gr.HTML("""
    <div style="text-align: center; padding: 20px;">
        <h1>🏠 Enhanced Singapore Housing Assistant</h1>
        <p style="font-size: 18px; color: #666;">
            AI-powered housing guidance with personalized recommendations
        </p>
    </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            chatbot_interface = gr.Chatbot(
                label="Housing Assistant Conversation",
                height=500,
                show_label=True,
                bubble_full_width=False
            )
            
            user_input = gr.Textbox(
                label="Your Message",
                placeholder="Ask about housing grants, property search, eligibility requirements, or any housing-related questions...",
                lines=3,
                show_label=True
            )
            
            with gr.Row():
                submit_btn = gr.Button("Send Message", variant="primary", size="lg")
                clear_btn = gr.Button("New Conversation", variant="secondary")
        
        with gr.Column(scale=1):
            gr.Markdown("### 🎯 Quick Start")
            
            sample_queries = [
                "What housing grants am I eligible for as a Singapore citizen?",
                "I earn $6000/month, what's my housing budget?",
                "Compare BTO vs resale HDB flats"
            ]
            
            sample_buttons = []
            for i, query in enumerate(sample_queries):
                btn = gr.Button(query, size="sm")
                sample_buttons.append(btn)
            
            gr.Markdown("### ℹ️ System Status")
            status_md = f"""
            - **Context Management**: {'✅ Active' if context_manager else '❌ Fallback'}
            - **RAG Knowledge**: {'✅ ' + rag_status if RAG_AVAILABLE else '❌ Not available'}
            - **Web Search**: ✅ Active
            """
            gr.Markdown(status_md)
    
    # Session state
    session_state = gr.State()
    
    def process_chat(message, history, session_id):
        """Process chat with proper error handling"""
        if not message or not message.strip():
            return history, "", session_id
        
        try:
            history = history or []
            history.append([message, None])
            
            response, new_session_id = chat_with_enhanced_housing_bot(message, session_id)
            history[-1][1] = response
            
            return history, "", new_session_id
        except Exception as e:
            logger.error(f"Error in process_chat: {e}")
            if history:
                history[-1][1] = f"Error processing message: {str(e)}"
            return history, "", session_id
    
    def set_input(query):
        """Set input field to sample query"""
        return query
    
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
        lambda: ([], "", None),
        outputs=[chatbot_interface, user_input, session_state]
    )
    
    # Sample button handlers
    for btn, query in zip(sample_buttons, sample_queries):
        btn.click(
            lambda q=query: q,
            outputs=user_input
        )

if __name__ == "__main__":
    logger.info("🚀 Launching Enhanced Singapore Housing Assistant")
    logger.info(f"Features: Context Management {'✅' if context_manager else '❌'}, RAG Knowledge {'✅' if RAG_AVAILABLE else '❌'}")
    
    try:
        iface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,  # Set to True for public sharing
            show_error=True,
            quiet=False
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        # Cleanup resources
        logger.info("Cleaning up resources...")
        try:
            if 'iface' in locals():
                iface.close()
        except:
            pass
'''