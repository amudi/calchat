import chainlit as cl
from langchain_core.runnables.history import RunnableWithMessageHistory
import json
import traceback
from app.api.chat import create_agent, session_manager
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Map of tool names to descriptions for better UI display
TOOL_DESCRIPTIONS = {
    "get_available_slots": "Check available time slots for scheduling",
    "book_new_appointment": "Book a new appointment",
    "get_user_bookings": "Find existing bookings by user",
    "get_booking_by_uid": "Get details of a specific booking",
    "reschedule_appointment": "Reschedule an existing appointment",
    "cancel_appointment": "Cancel an existing appointment"
}

HELP_TEXT = """
# CalChat - Cal.com Calendar Assistant

This is an AI-powered chat interface for managing your Cal.com calendar. You can ask me to:

- **Find available slots**: "What times are available next week for a 30-minute meeting?"
- **Book a meeting**: "Schedule a 1-hour meeting with John at john@example.com on Friday at 2pm"
- **View your schedule**: "Show me my meetings for next week"
- **Reschedule a meeting**: "Move my meeting with Sarah to Thursday at 3pm"
- **Cancel a meeting**: "Cancel my meeting with Mark on Friday"
- **Get event types**: "What meeting types do I have available?"
"""

class User:
    def __init__(self, id, name, metadata=None):
        self.id = id
        self.name = name
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "metadata": self.metadata
        }

@cl.on_chat_start
async def start():
    """Initialize the chat session"""
    # Display help information
    await cl.Message(content=HELP_TEXT).send()
    
    # Create the agent
    try:
        agent_executor = create_agent()
        
        # Wrap with message history for session persistence
        agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            lambda session_id: session_manager.get_history(session_id),
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        # Store the agent in the user session
        cl.user_session.set("agent", agent_with_chat_history)
        cl.user_session.set("chat_history", [])
        
        # Create UI elements for the tools
        tools_md = "## Available Tools\n\n"
        for tool_name, description in TOOL_DESCRIPTIONS.items():
            tools_md += f"- **{tool_name}**: {description}\n"
        
        # Add tools element to the sidebar using Text component instead of Element
        tools_text = cl.Text(
            content=tools_md,
            name="tools",
            display="side"
        )
        
        # Create a welcome message first
        welcome_msg = cl.Message(
            content="Welcome to CalChat! How can I help you with your calendar today?"
        )
        await welcome_msg.send()
        
        # Now send the tools text with the welcome message ID
        await tools_text.send(for_id=welcome_msg.id)
        
    except Exception as e:
        error_msg = f"Error initializing the chat: {str(e)}"
        traceback_str = traceback.format_exc()
        
        await cl.Message(
            content=f"❌ {error_msg}\n\n```\n{traceback_str}\n```",
            author="System Error",
            type="error"
        ).send()

@cl.on_message
async def main(message: cl.Message):
    """Process user messages with LangChain agent"""
    try:
        # Get the agent from the user session
        agent = cl.user_session.get("agent")
        
        # Get session ID for message history
        session_id = cl.user_session.get("id")
        
        # Create a message element for processing indication
        processing_msg = cl.Message(
            content="Thinking...",
            author="System",
            type="system"
        )
        await processing_msg.send()
        
        # Create Chainlit callback handler with only supported parameters
        cb = cl.LangchainCallbackHandler(
            stream_final_answer=True
        )
        
        # Run the agent with proper message history and callbacks
        response = await cl.make_async(agent.invoke)(
            {"input": message.content},
            config={"configurable": {"session_id": session_id}},
            callbacks=[cb]
        )
        
        # Remove the processing message
        await processing_msg.remove()
        
        # Explicitly send the AI's response as a message
        await cl.Message(content=response["output"]).send()
        
        # Update chat history in the session
        chat_history = cl.user_session.get("chat_history")
        chat_history.append({"role": "user", "content": message.content})
        chat_history.append({"role": "assistant", "content": response["output"]})
        cl.user_session.set("chat_history", chat_history)
        
    except Exception as e:
        error_msg = f"Error processing your message: {str(e)}"
        traceback_str = traceback.format_exc()
        
        await cl.Message(
            content=f"❌ {error_msg}\n\n```\n{traceback_str}\n```",
            author="System Error",
            type="error"
        ).send()

@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> cl.User:
    """Optional authentication callback"""
    logger.info(f"Auth attempt: {username}")
    # For demo purposes, accept any non-empty username/password
    if username and password:
        logger.info(f"Authentication successful for {username}")
        user = cl.User(
            identifier=username,
            metadata={"username": username}
        )
        logger.info(f"Created user object: {user}")
        return user
    logger.info("Authentication failed: empty username or password")
    return None

@cl.action_callback("help")
async def on_help_action():
    """Show help information when the help action is clicked"""
    await cl.Message(content=HELP_TEXT).send()

@cl.on_settings_update
async def setup_agent(settings):
    """Update agent settings when user changes them"""
    print(f"Settings updated: {json.dumps(settings, indent=2)}") 
