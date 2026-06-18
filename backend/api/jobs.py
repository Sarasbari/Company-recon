import uuid
import asyncio
from typing import Dict

class HistoryQueue(asyncio.Queue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = []

    async def put(self, item):
        self.history.append(item)
        await super().put(item)

# In-memory job store mapping job_id -> HistoryQueue
job_queues: Dict[str, HistoryQueue] = {}

def create_job() -> str:
    """
    Creates a new research job and returns its unique ID.
    """
    job_id = str(uuid.uuid4())
    job_queues[job_id] = HistoryQueue()
    return job_id

def get_job_queue(job_id: str) -> HistoryQueue:
    """
    Retrieves the SSE event queue for a specific job ID.
    """
    return job_queues.get(job_id)

def delete_job_queue(job_id: str):
    """
    Deletes the job queue from the in-memory store to prevent memory leaks.
    """
    if job_id in job_queues:
        del job_queues[job_id]
