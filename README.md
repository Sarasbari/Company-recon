# Company-recon

An autonomous prospect intelligence research agent that compiles a full structured dossier from a single company name. Built from scratch with a custom Python ReAct agent loop (using raw Anthropic and Tavily APIs, no heavy frameworks like LangChain) and a premium, data-dense React + Tailwind CSS v4 frontend.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   React 18 + Vite + Tailwind CSS v4                        │
│   Pages: Home / Research Stream / History / Detail          │
│   Clerk SDK Wrapper (Auth + Stateful Mock)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / Server-Sent Events (SSE)
┌──────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                      │
│                                                             │
│  POST /research          → Start background agent loop      │
│  GET  /research/{id}/stream → SSE stream of ReAct steps    │
│  GET  /dossiers          → User's saved history archive     │
│  DELETE /dossiers/{id}   → Delete history entry             │
│                                                             │
│  Tools: web_search (Tavily) | fetch_page (BeautifulSoup4)    │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
company-recon/
├── backend/
│   ├── agent/             # ReAct Agent loop, test runner, and prompts
│   ├── api/               # FastAPI route definitions and auth middleware
│   ├── db/                # Supabase database wrapper & memory fallback
│   ├── tools/             # Search (Tavily) and Fetch (BeautifulSoup4) scraper tools
│   ├── main.py            # API entrypoint
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/    # Navbar, DossierReport, StreamLog, MockClerk, etc.
│   │   ├── pages/         # Home, Research stream, History archive, DossierDetail
│   │   ├── index.css      # Core styles & Tailwind imports
│   │   └── App.jsx        # Routing configuration
│   ├── vite.config.js     # Tailwind CSS v4 integration
│   └── package.json       # Node dependencies
├── docs/                  # PRD, TRD, UI/UX briefs, and user flows
└── .env                   # Local environment variables
```

---

## How to Run the Project

This project supports **Mock Mode** out-of-the-box! If you don't have active API keys for Anthropic, Tavily, Clerk, or Supabase, the project will automatically fall back to stateful local mock implementations (simulated streaming steps, custom dossier mock synthesis, and in-memory login and history persistence).

### Prerequisites
- **Python** (version 3.11 or later)
- **Node.js** (version 18 or later)

---

### Step 1: Clone the Repo and Configure the Environment
1. Copy the environment template to create your `.env` file in the root directory:
   ```bash
   cp .env.template .env
   ```
2. By default, `.env` is initialized with mock keys. To use real APIs, fill in the actual keys:
   - `GEMINI_API_KEY`: Google Gemini Developer API key (free tier alternative for Gemini 1.5 Flash)
   - `ANTHROPIC_API_KEY`: Anthropic developer key (optional alternative for Claude 3.5 Haiku & Sonnet)
   - `TAVILY_API_KEY`: Tavily Search API key (free tier is sufficient)
   - `SUPABASE_URL` & `SUPABASE_SERVICE_ROLE_KEY`: Supabase project database keys
   - `CLERK_SECRET_KEY` & `CLERK_PUBLISHABLE_KEY`: Clerk authentication keys

---

### Step 2: Start the FastAPI Backend Server
1. Navigate to the project root and create a Python virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On macOS/Linux:
   source venv/bin/activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run the FastAPI development server:
   ```bash
   python -m backend.main
   ```
   *The backend API will boot up on **http://localhost:8000**.*

---

### Step 3: Start the React Frontend
1. Open a new terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite client dev server:
   ```bash
   npm run dev
   ```
   *The client app will launch on **http://localhost:5173**.*

---

## Verifying the Installation

- Open **http://localhost:5173** in your browser.
- **Mock Mode Testing**: Type `Razorpay` in the search box and click **Research**. You will watch the agent's reasoning steps, tool calls, and observations animate in real time before rendering the completed prospect dossier!
- **Auth Testing**: Click **Sign In** in the top right. In mock mode, this will instantly log you in statefully in memory (showing a custom avatar and history counts). Run a search while logged in, and verify it saves to the **History** tab where you can hover to preview, click to open, or delete saved dossiers.
