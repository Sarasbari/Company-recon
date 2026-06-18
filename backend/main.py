import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environmental variables
load_dotenv()

from backend.api.routes import research, dossiers

# Initialize FastAPI App
app = FastAPI(
    title="company-recon API",
    description="Backend API for the autonomous company prospect intelligence agent",
    version="1.0"
)

# Configure CORS Middleware
# Allows request from Vite dev server (default http://localhost:5173) and production deploys
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, allow all. Refine for production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(research.router)
app.include_router(dossiers.router)

@app.get("/")
async def health_check():
    """
    Health check endpoint. Indicates whether server is active and configuration status.
    """
    gemini_configured = bool(os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") not in ("mock_key", "your_gemini_api_key_here", ""))
    anthropic_configured = bool(os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") not in ("mock_key", "your_anthropic_api_key_here", ""))
    tavily_configured = bool(os.getenv("TAVILY_API_KEY") and os.getenv("TAVILY_API_KEY") not in ("mock_key", "your_tavily_api_key_here", ""))
    supabase_configured = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_URL") not in ("mock_url", "your_supabase_url_here", ""))
    
    return {
        "status": "healthy",
        "mock_mode": not ((anthropic_configured or gemini_configured) and tavily_configured),
        "config": {
            "gemini_api": "configured" if gemini_configured else "mock/missing",
            "anthropic_api": "configured" if anthropic_configured else "mock/missing",
            "tavily_api": "configured" if tavily_configured else "mock/missing",
            "supabase": "configured" if supabase_configured else "mock/missing",
            "clerk": "configured" if os.getenv("CLERK_PUBLISHABLE_KEY") and os.getenv("CLERK_PUBLISHABLE_KEY") != "mock_key" else "missing"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
