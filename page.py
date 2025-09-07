# page.py - Updated to use consolidated tools
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
logger.info("Starting Enhanced Housing Assistant with Consolidated Tools + RAG + MCP")

# Import consolidated tools and check availability
try:
    from tools_consolidated import tool_registry, get_tool_status
    from tools_consolidated.registry import tool_registry
    CONSOLIDATED_TOOLS_AVAILABLE = True
    logger.info("✅ Consolidated tools loaded successfully")
    
    # Log tool status
    status = get_tool_status()
    available_tools = status['available_tools']
    total_tools = status['total_tools'] 
    logger.info(f"Tool Status: {available_tools}/{total_tools} tools available")
    
except ImportError as e:
    logger.warning(f"⚠️ Consolidated tools not available: {e}")
    CONSOLIDATED_TOOLS_AVAILABLE = False

# Import orchestrator agent (updated to use consolidated tools)
try:
    from agents.orchestrator_agent import orchestrator
    logger.info("✅ Orchestrator agent loaded")
except ImportError as e:
    logger.error(f"❌ Failed to load orchestrator agent: {e}")
    raise

# Import context manager
try:
    from core.mcp_context_manager import MCPContextManager
    MCP_AVAILABLE = True
    logger.info("✅ MCP Context Manager available")
except ImportError as e:
    logger.warning(f"⚠️ MCP Context Manager not available: {e}")
    MCP_AVAILABLE = False

# Validate AWS RAG system if available
try:
    if CONSOLIDATED_TOOLS_AVAILABLE:
        from ragtool.aws_rag_tools import validate_aws_rag_configuration
        rag_status = validate_aws_rag_configuration()
        logger.info(f"AWS RAG Status: {rag_status}")
    else:
        logger.info("AWS RAG Status: Using legacy validation")
except Exception as e:
    logger.warning(f"AWS RAG validation failed: {e}")

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
        """Extract profile information from user message"""
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
                
                # Note: Removed emoji as per guidelines
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
    system_status = "Consolidated Tools" if CONSOLIDATED_TOOLS_AVAILABLE else "Legacy Tools"
    mcp_status = "Context Management" if MCP_AVAILABLE else "Basic Mode"
    
    gr.HTML(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #4f46e5, #3b82f6); color: white; border-radius: 12px; margin-bottom: 20px;">
        <h1 style="margin: 0; font-size: 2em;">Enhanced Singapore Housing Assistant</h1>
        <p style="font-size: 18px; margin: 5px 0 0;">AI-powered housing guidance with personalized recommendations</p>
        <p style="font-size: 14px; margin: 5px 0 0; opacity: 0.8;">Status: {system_status} | {mcp_status}</p>
    </div>
    """)

    with gr.Row():
        # Main conversation area
        with gr.Column(scale=3):
            chatbot_interface = gr.Chatbot(
                type="messages",
                label="Chat with Housing Assistant",
                height=500,
                show_label=True
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
                "Compare BTO vs resale HDB flats"
            ]
            
            sample_buttons = []
            for i, query in enumerate(sample_queries):
                btn = gr.Button(query, size="sm")
                sample_buttons.append(btn)
            
            gr.Markdown("### System Status")
            
            # Dynamic status based on available systems
            if CONSOLIDATED_TOOLS_AVAILABLE:
                try:
                    tool_status = get_tool_status()
                    available_count = tool_status['available_tools']
                    total_count = tool_status['total_tools']
                    status_md = f"""
                    - **Tools**: {available_count}/{total_count} available
                    - **Context Management**: {'Active' if MCP_AVAILABLE else 'Basic'}
                    - **AWS RAG**: {'Active' if 'aws' in tool_status.get('categories', {}) else 'Unavailable'}
                    """
                except:
                    status_md = f"""
                    - **Tools**: Consolidated tools active
                    - **Context Management**: {'Active' if MCP_AVAILABLE else 'Basic'}
                    - **Status**: All systems operational
                    """
            else:
                status_md = f"""
                - **Tools**: Legacy mode
                - **Context Management**: {'Active' if MCP_AVAILABLE else 'Basic'}
                - **Note**: Running in compatibility mode
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