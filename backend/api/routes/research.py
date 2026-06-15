import json
import asyncio
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict

from backend.api.jobs import create_job, get_job_queue
from backend.api.middleware.auth import get_user_id
from backend.agent.react_loop import run_agent
from backend.db.supabase import save_dossier, update_dossier

router = APIRouter(prefix="/research", tags=["research"])

# In-memory store for tracking job status and results (crucial for guest users and polling)
job_status_store: Dict[str, dict] = {}

class ResearchRequest(BaseModel):
    company: str = Field(..., min_length=2, description="The name of the company to research.")
    website: Optional[str] = Field(None, description="Optional website URL hint.")

async def run_agent_background(company: str, job_id: str, queue: asyncio.Queue, user_id: Optional[str], db_dossier_id: Optional[str]):
    """
    Background worker that runs the agent loop and synchronizes state updates.
    """
    job_status_store[job_id] = {"status": "running", "dossier": None}
    
    try:
        if db_dossier_id:
            await update_dossier(db_dossier_id, "running")
            
        dossier = await run_agent(company, queue)
        
        job_status_store[job_id] = {"status": "complete", "dossier": dossier}
        if db_dossier_id:
            await update_dossier(db_dossier_id, "complete", dossier)
            
    except Exception as e:
        print(f"Background agent execution failed for job {job_id}: {str(e)}")
        job_status_store[job_id] = {"status": "failed", "error": str(e)}
        if db_dossier_id:
            await update_dossier(db_dossier_id, "failed")

@router.post("")
async def start_research(request: Request, payload: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Kicks off a research job.
    If authenticated, links it to the user's Supabase account and returns the db dossier id.
    """
    company_name = payload.company.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    user_id = await get_user_id(request)
    job_id = create_job()
    queue = get_job_queue(job_id)
    
    job_status_store[job_id] = {"status": "pending", "dossier": None}
    
    db_dossier_id = None
    if user_id:
        # Save record in Supabase / In-Memory history as pending
        db_dossier_id = await save_dossier(user_id=user_id, company=company_name, status="pending")

    # Start agent loop in background
    background_tasks.add_task(run_agent_background, company_name, job_id, queue, user_id, db_dossier_id)

    return {
        "job_id": job_id,
        "dossier_id": db_dossier_id,
        "status": "pending"
    }

@router.get("/{job_id}/stream")
async def stream_research(job_id: str):
    """
    Establishes an SSE stream connection to deliver live agent steps.
    """
    queue = get_job_queue(job_id)
    if not queue:
        raise HTTPException(status_code=404, detail="Research job stream not found")

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                
                # Check for completion or failure states
                if event["type"] in ("complete", "error"):
                    break
        except asyncio.CancelledError:
            # Handle client disconnect gracefully
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/{job_id}")
async def get_research_status(job_id: str):
    """
    Polls the current status of a research job.
    """
    status_info = job_status_store.get(job_id)
    if not status_info:
        raise HTTPException(status_code=404, detail="Research job not found")
    return status_info
