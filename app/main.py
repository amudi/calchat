"""
Main entry point for the CalChat application.
Handles API routes for the chat interface.
"""

import json
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
from chainlit.utils import mount_chainlit

from app.api.chat import generate_openai_stream

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(title="CalChat API", description="API for the CalChat application")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
async def root():
    """
    Root endpoint that returns a welcome message.
    """
    return {"message": "Welcome to CalChat API"}

@app.post("/chat")
async def chat(request: Request):
    """
    Chat endpoint that receives a message and returns a response.
    
    Args:
        request: The request object containing the message and session_id
        
    Returns:
        A streaming response with the chat response
    """
    # Parse the request
    data = await request.json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")
    
    logger.info(f"Received message: '{message[:50]}...' with session_id: {session_id}")
    
    # Define the streaming function
    async def stream_response():
        async for response_chunk in generate_openai_stream(message, session_id, format_as_sse=True):
            yield response_chunk
    
    # Return a streaming response
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )

@app.post("/message")
async def message(request: Request):
    """
    Message endpoint for Chainlit frontend.
    
    Args:
        request: The request object containing the content
        
    Returns:
        A streaming response with the chat response
    """
    # Parse the request
    data = await request.json()
    content = data.get("content", "")
    session_id = data.get("session_id", "default")
    
    logger.info(f"Received message from Chainlit: '{content[:50]}...' with session_id: {session_id}")
    
    # Define the streaming function
    async def stream_response():
        async for response_chunk in generate_openai_stream(content, session_id, format_as_sse=True):
            yield response_chunk
    
    # Return a streaming response
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat.
    
    Args:
        websocket: The WebSocket connection
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            data_json = json.loads(data)
            message = data_json.get("message", "")
            session_id = data_json.get("session_id", "default")
            
            logger.info(f"Received WebSocket message: '{message[:50]}...' with session_id: {session_id}")
            
            # Generate response
            async for response_chunk in generate_openai_stream(message, session_id):
                await websocket.send_text(response_chunk)
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()

# Mount Chainlit frontend to the FastAPI app
mount_chainlit(app=app, target="app/chainlit_app.py", path="/chainlit")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
