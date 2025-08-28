from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from services import PropertyAnalysisService
from models import PropertyAnalysisRequest, PropertyAnalysisResponse, ChatRequest
from typing import Optional
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Property Analysis API",
    description="AI-powered property analysis system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analysis_service = PropertyAnalysisService()
executor = ThreadPoolExecutor(max_workers=10)

@app.get("/")
async def root():
    """Root endpoint with basic API info and active task count"""
    active_count = analysis_service.get_active_tasks_count()
    return {
        "message": "Property Analysis API",
        "status": "operational",
        "active_tasks": active_count,
        "endpoints": {
            "analyze": "/api/analyze",
            "status": "/api/status/{task_id}",
            "chat": "/api/chat",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with active task count"""
    active_count = analysis_service.get_active_tasks_count()
    return {
        "status": "healthy",
        "active_tasks": active_count
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Handle chat messages from users with follow-up questions about property analysis.
    """
    try:
        logger.info(f"Received chat message from session {request.session_id}: {request.message[:100]}...")
        
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        response = await process_chat_message(
            message=request.message,
            context=request.context,
            address=request.address,
            session_id=request.session_id
        )
        
        logger.info(f"Chat response generated for session {request.session_id}")
        
        return {
            "response": response,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return {
            "response": "Sorry, I encountered an error while processing your message. Please try again.",
            "status": "error",
            "error": str(e)
        }

async def process_chat_message(message: str, context: Optional[str], address: Optional[str], session_id: str) -> str:
    """
    Process chat message using the existing analysis system's LLM.
    """
    try:
        logger.info(f"Processing chat message for session {session_id}")
        
        from llm_integration import LLMProcessor
        
        llm_processor = LLMProcessor()
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            llm_processor.process_chat_message,
            message,
            context,
            address,
            session_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return "I apologize, but I'm having trouble processing your question right now. Please try again."

async def run_analysis_in_background(task_id: str, address: str, depth):
    """Run analysis in background using thread pool"""
    try:
        logger.info(f"Starting background analysis for task {task_id}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            analysis_service.analyze_sync,
            task_id,
            address,
            depth
        )
        logger.info(f"Background analysis completed for task {task_id}")
    except Exception as e:
        logger.error(f"Background analysis failed for task {task_id}: {e}", exc_info=True)

@app.post("/api/analyze")
async def analyze_property(
    request: PropertyAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Start property analysis asynchronously and return task ID"""
    try:
        logger.info(f"Received analysis request for: {request.address}")
        
        active_count = analysis_service.get_active_tasks_count()
        if active_count >= 10:
            raise HTTPException(
                status_code=503,
                detail="Server at capacity, please try again later"
            )
        
        if not request.address or len(request.address) < 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid address provided"
            )
        
        analysis_id = str(uuid.uuid4())
        analysis_service._initialize_task(analysis_id, request.address)
        
        background_tasks.add_task(
            run_analysis_in_background,
            analysis_id,
            request.address,
            request.analysis_depth
        )
        
        return {
            "analysis_id": analysis_id,
            "success": True,
            "message": "Analysis started successfully",
            "status_endpoint": f"/api/status/{analysis_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the current status of an analysis task"""
    task_info = analysis_service.get_task_status(task_id)
    if not task_info:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )
    return task_info

@app.post("/api/analyze-sync", response_model=PropertyAnalysisResponse)
async def analyze_property_sync(
    request: PropertyAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """Run synchronous property analysis (blocking, fallback endpoint)"""
    try:
        logger.info(f"Received sync analysis request for: {request.address}")
        
        if not request.address or len(request.address) < 1:
            raise HTTPException(
                status_code=400,
                detail="Invalid address provided"
            )
        
        result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                executor,
                analysis_service.analyze_sync,
                None,
                request.address,
                request.analysis_depth
            ),
            timeout=300
        )
        
        background_tasks.add_task(
            analysis_service.log_to_langsmith,
            request.address,
            result
        )
        
        return PropertyAnalysisResponse(
            analysis_id=str(uuid.uuid4()),
            success=True,
            data=result,
            message="Analysis completed successfully"
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Analysis timed out"
        )
    except Exception as e:
        logger.error(f"Sync analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)