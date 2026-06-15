import uuid
import asyncio
from typing import Dict

# In-memory job store mapping job_id -> asyncio.Queue
job_queues: Dict[str, asyncio.Queue] = {}

def create_job() -> str:
    """
    Creates a new research job and returns its unique ID.
    """
    job_id = str(uuid.uuid4())
    job_queues[job_id] = asyncio.Queue()
    return job_id

def get_job_queue(job_id: str) -> asyncio.Queue:
    """
    Retrieves the SSE event queue for a specific job ID.
    """
    return job_queues.get(job_id)
