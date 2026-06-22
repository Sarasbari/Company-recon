import json
import asyncio
import time
from collections import defaultdict
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal

from backend.logging_config import logger

from backend.api.jobs import create_job, get_job_queue
from backend.api.middleware.auth import get_user_id
from backend.agent.react_loop import run_agent
from backend.db.supabase import save_dossier, update_dossier, get_dossier_by_id_only

router = APIRouter(prefix="/research", tags=["research"])

# In-memory store for tracking job status and results (crucial for guest users and polling)
job_status_store: Dict[str, dict] = {}

# Concurrent jobs limit (Semaphore)
concurrent_jobs_semaphore = asyncio.Semaphore(3)

# Per-IP Rate Limiter: client_ip -> list of timestamps
rate_limit_store = defaultdict(list)
RATE_LIMIT_RUNS = 5
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

class ResearchRequest(BaseModel):
    company: str = Field(..., min_length=2, description="The name of the company to research.")
    website: Optional[str] = Field(None, description="Optional website URL hint.")
    purpose: Literal["general", "sales", "investor", "job_seeker"] = "general"

async def cleanup_job_status_delayed(job_id: str, delay: int = 300):
    """
    Deletes the job from the in-memory status store after a delay to allow the client to read it,
    preventing memory leaks.
    """
    await asyncio.sleep(delay)
    if job_id in job_status_store:
        del job_status_store[job_id]

async def run_agent_background(company: str, job_id: str, queue: asyncio.Queue, user_id: Optional[str], db_dossier_id: Optional[str], purpose: str = "general"):
    """
    Background worker that runs the agent loop under a concurrency lock.
    """
    # Wait for slot in concurrency semaphore
    async with concurrent_jobs_semaphore:
        job_status_store[job_id] = {"status": "running", "dossier": None}
        
        try:
            if db_dossier_id:
                await update_dossier(db_dossier_id, "running")
                
            dossier = await run_agent(company, queue, purpose)
            
            job_status_store[job_id] = {"status": "complete", "dossier": dossier}
            if db_dossier_id:
                await update_dossier(db_dossier_id, "complete", dossier)
                
        except Exception as e:
            logger.error(f"Background agent execution failed for job {job_id}: {str(e)}")
            job_status_store[job_id] = {"status": "failed", "error": str(e)}
            if db_dossier_id:
                await update_dossier(db_dossier_id, "failed")
        finally:
            from backend.api.jobs import delete_job_queue
            delete_job_queue(job_id)
            # Schedule a background task to clean up the in-memory status store after 5 minutes
            asyncio.create_task(cleanup_job_status_delayed(job_id, delay=300))

@router.post("")
async def start_research(request: Request, payload: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Kicks off a research job.
    If authenticated, links it to the user's Supabase account and returns the db dossier id.
    Enforces hourly per-IP rate limits.
    """
    # IP Rate Limiting
    client_ip = request.client.host if request.client else "unknown_ip"
    now = time.time()
    
    # Filter active runs within the sliding window
    active_runs = [t for t in rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW]
    rate_limit_store[client_ip] = active_runs
    
    if len(active_runs) >= RATE_LIMIT_RUNS:
        # Calculate time remaining until the oldest run falls out of the window
        reset_time_minutes = int((RATE_LIMIT_WINDOW - (now - active_runs[0])) / 60) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_RUNS} researches per hour. Try again in {reset_time_minutes} minutes."
        )

    company_name = payload.company.strip()
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    # Record current execution timestamp
    rate_limit_store[client_ip].append(now)

    user_id = await get_user_id(request)
    job_id = create_job()
    queue = get_job_queue(job_id)
    
    job_status_store[job_id] = {"status": "pending", "dossier": None}
    
    db_dossier_id = None
    if user_id:
        # Save record in Supabase / In-Memory history as pending
        db_dossier_id = await save_dossier(user_id=user_id, company=company_name, status="pending", dossier_id=job_id)

    # Start agent loop in background
    background_tasks.add_task(run_agent_background, company_name, job_id, queue, user_id, db_dossier_id, payload.purpose)

    return {
        "job_id": job_id,
        "dossier_id": db_dossier_id,
        "status": "pending",
        "remaining_runs": RATE_LIMIT_RUNS - len(rate_limit_store[client_ip])
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
    Falls back to checking the persistent database if not found in the memory store.
    """
    status_info = job_status_store.get(job_id)
    if not status_info:
        db_record = await get_dossier_by_id_only(job_id)
        if db_record:
            return {
                "status": db_record.get("status"),
                "dossier": db_record.get("dossier"),
                "error": None
            }
        raise HTTPException(status_code=404, detail="Research job not found")
    return status_info

@router.get("/debug/{job_id}")
async def get_job_debug(job_id: str, request: Request):
    """
    Gated endpoint to retrieve raw ReAct agent steps for a completed job.
    Loads from in-memory cache or persistent database, and validates ownership/local dev access.
    """
    status_info = job_status_store.get(job_id)
    dossier = None
    db_record = None
    error = None
    status = None
    
    if status_info:
        status = status_info.get("status")
        dossier = status_info.get("dossier")
        error = status_info.get("error")
    else:
        db_record = await get_dossier_by_id_only(job_id)
        if db_record:
            status = db_record.get("status")
            dossier = db_record.get("dossier")
            
    if not dossier:
        if status:
            return {
                "job_id": job_id,
                "status": status,
                "error": error,
                "steps": []
            }
        raise HTTPException(status_code=404, detail="Job or dossier not found")
        
    # Gating and authorization check (whichever best suited for production)
    user_id = await get_user_id(request)
    dossier_user_id = db_record.get("user_id") if db_record else None
    
    # We consider it a local request if client is localhost
    is_local = request.client and request.client.host in ("127.0.0.1", "localhost", "::1")
    
    # In production, if a user ID is bound to the record, the requester must own it
    if dossier_user_id and dossier_user_id != user_id and not is_local:
        raise HTTPException(status_code=403, detail="Access denied: You do not own this research dossier")
        
    metadata = dossier.get("agent_metadata", {})
    return {
        "job_id": job_id,
        "company": dossier.get("company"),
        "model_used": metadata.get("model_used"),
        "duration_seconds": metadata.get("duration_seconds"),
        "steps": metadata.get("steps", [])
    }
