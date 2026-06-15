import sys
import asyncio
import os
from dotenv import load_dotenv

# Add parent directory to path so python can import backend packages properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load environment variables from .env
load_dotenv()

from backend.agent.react_loop import run_agent

async def main():
    company = sys.argv[1] if len(sys.argv) > 1 else "Razorpay"
    print(f"Initializing ReAct agent for: '{company}'...")
    
    queue = asyncio.Queue()
    
    async def log_stream():
        while True:
            event = await queue.get()
            etype = event.get("type")
            if etype == "start":
                print(f"\n>>> [START] Researching {event.get('company')}...")
            elif etype == "reason":
                print(f"\n[REASON] {event.get('text')}")
            elif etype == "action":
                print(f"\n[ACTION] Tool: {event.get('tool')} | Input: {event.get('input')}")
            elif etype == "observation":
                print(f"\n[OBSERVE] Summary: {event.get('summary')}")
            elif etype == "complete":
                print("\n>>> [COMPLETE] Dossier Generated:")
                print(json.dumps(event.get("dossier"), indent=2))
                break
            elif etype == "error":
                print(f"\n>>> [ERROR] {event.get('message')}")
                break
            queue.task_done()

    import json
    
    agent_task = asyncio.create_task(run_agent(company, queue))
    log_task = asyncio.create_task(log_stream())
    
    await asyncio.gather(agent_task, log_task)

if __name__ == "__main__":
    asyncio.run(main())
