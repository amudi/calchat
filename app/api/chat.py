"""
Chat module for handling the conversation with the user.
Implements an LLM-based agent that can manage calendar-related tasks.
"""

import os
import json
import time
import asyncio
from typing import AsyncGenerator
from dotenv import load_dotenv
import pathlib
import logging
import traceback

import chainlit as cl
# LangChain imports
from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the .env file
current_dir = pathlib.Path(__file__).parent.parent
env_path = current_dir / '.env'

# Load environment variables from the specific .env file
load_dotenv(dotenv_path=env_path)

# Explicitly set the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
if api_key and openai_model:
    logger.info(f"API key loaded successfully: {api_key[:5]}...")
    logger.info(f"OpenAI model loaded successfully: {openai_model}")
else:
    logger.error("OPENAI_API_KEY or OPENAI_MODEL not found in .env file")

# Constants
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours
MAX_SESSIONS = 1000

# Import system prompt
from ..prompts import SYSTEM_PROMPT  # noqa: E402

# Import tool functions
from ..tools import (  # noqa: E402
    get_available_slots,
    book_new_appointment,
    get_user_bookings,
    get_booking_by_uid,
    reschedule_appointment,
    cancel_appointment
)

# Create the tools list
tools = [
    get_available_slots, 
    book_new_appointment, 
    get_user_bookings, 
    get_booking_by_uid, 
    reschedule_appointment, 
    cancel_appointment
]

# Create prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Create the agent
def create_agent():
    """
    Create a LangChain agent with the tools and prompt.
    
    Returns:
        An AgentExecutor ready to process messages
    """
    llm = ChatOpenAI(model=openai_model, temperature=0.3, api_key=api_key)
    
    # Create the agent with the LLM, tools, and prompt
    agent = create_openai_tools_agent(
        llm=llm,
        tools=tools,
        prompt=prompt
    )
    
    # Create an agent executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
    
    return agent_executor

# Session management with expiry timestamps
class SessionManager:
    """
    Manages conversation sessions and their message histories.
    Handles session creation, retrieval, and cleanup of expired sessions.
    """
    
    def __init__(self, expiry_hours=SESSION_EXPIRY_HOURS, max_sessions=MAX_SESSIONS):
        """
        Initialize the session manager.
        
        Args:
            expiry_hours: Number of hours after which a session expires
            max_sessions: Maximum number of sessions to store
        """
        self.sessions = {}  # {session_id: {"history": ChatMessageHistory, "last_access": timestamp}}
        self.expiry_hours = expiry_hours
        self.max_sessions = max_sessions
    
    def get_history(self, session_id):
        """
        Get or create a message history for this session.
        
        Args:
            session_id: Unique identifier for the session
            
        Returns:
            A ChatMessageHistory object for the session
        """
        # Clean expired sessions periodically
        self._clean_expired_sessions()
        
        # Check if session exists
        if session_id in self.sessions:
            # Update last access time
            self.sessions[session_id]["last_access"] = time.time()
            return self.sessions[session_id]["history"]
        
        # Create new session
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest session if at capacity
            self._remove_oldest_session()
        
        # Create new history
        history = ChatMessageHistory()
        self.sessions[session_id] = {
            "history": history,
            "last_access": time.time()
        }
        return history
    
    def _clean_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expiry_seconds = self.expiry_hours * 3600
        
        expired_sessions = [
            session_id for session_id, data in self.sessions.items()
            if (current_time - data["last_access"]) > expiry_seconds
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Removed expired session: {session_id}")
    
    def _remove_oldest_session(self):
        """Remove the oldest (least recently accessed) session."""
        if not self.sessions:
            return
        
        oldest_session_id = min(
            self.sessions.keys(),
            key=lambda session_id: self.sessions[session_id]["last_access"]
        )
        
        del self.sessions[oldest_session_id]
        logger.info(f"Removed oldest session: {oldest_session_id}")

# Initialize session manager
session_manager = SessionManager()

async def generate_openai_stream(content: str, session_id: str = "default", format_as_sse: bool = False) -> AsyncGenerator[str, None]:
    """
    Generate a streaming response using the LangChain agent.
    
    Args:
        content: The user's message
        session_id: A unique identifier for the conversation session
        format_as_sse: Whether to format the output as SSE messages (for HTTP streaming)
    
    Yields:
        Chunks of the response as they are generated, optionally formatted as SSE
    """
    logger.info(f"Processing request for session {session_id}: {content[:50]}...")
    
    # Get or create a message history for this session
    message_history = session_manager.get_history(session_id)
    
    # Create the agent
    agent_executor = create_agent()
    
    # Wrap the agent with message history
    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        lambda sid: session_manager.get_history(sid),
        input_messages_key="input",
        history_messages_key="chat_history",
    )
    
    # Add the new human message to history
    message_history.add_message(HumanMessage(content=content))
    
    # Run the agent with streaming
    try:
        # Process with the agent
        result = await agent_with_chat_history.ainvoke(
            {"input": content},
            config={"configurable": {"session_id": session_id}}
        )
        
        # Get the AI response
        ai_message = result["output"]
        
        # Save the AI message to history
        message_history.add_message(AIMessage(content=ai_message))
        
        # Stream the response with natural break points
        sentences = []
        current_sentence = ""
        
        # Split by common sentence ends while preserving them
        for char in ai_message:
            current_sentence += char
            
            # Send at natural breaks (end of sentences or long chunks)
            if char in ['.', '!', '?', '\n'] or len(current_sentence) >= 80:
                sentences.append(current_sentence)
                current_sentence = ""
        
        # Add any remaining text
        if current_sentence:
            sentences.append(current_sentence)
        
        # Yield each sentence or chunk
        for sentence in sentences:
            if format_as_sse:
                yield f"data: {json.dumps({'content': sentence})}\n\n"
            else:
                yield sentence
            await asyncio.sleep(0.01)  # Small delay for more natural streaming
            
    except Exception as e:
        error_message = f"Error processing request: {str(e)}"
        logger.error(error_message)
        logger.error(traceback.format_exc())
        
        if format_as_sse:
            yield f"data: {json.dumps({'content': error_message})}\n\n"
        else:
            yield error_message 