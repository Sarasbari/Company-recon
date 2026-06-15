# Implementation Plan — company-recon
Version: 1.0 | Status: Draft

---

## Guiding Rule

Build the agent core first. Don't touch the frontend until the agent returns a real dossier in your terminal. A polished UI on a broken agent is wasted effort.

---

## Phase 0 — Project Setup (Day 1, ~2 hours)

**Goal:** Repo, environment, all API keys verified working with hello-world calls.

- [ ] Create GitHub repo `company-recon`
- [ ] Set up monorepo structure:
  ```
  company-recon/
  ├── backend/
  │   ├── agent/
  │   ├── api/
  │   ├── tools/
  │   ├── main.py
  │   └── requirements.txt
  ├── frontend/
  │   ├── src/
  │   └── package.json
  └── docs/         ← PRD, TRD, etc live here
  ```
- [ ] Create `.env` file, add to `.gitignore`
- [ ] Sign up for Tavily (free tier), get API key
- [ ] Add $5 credit to Anthropic API account, get API key
- [ ] Create Supabase project, note URL + service role key
- [ ] Create Clerk app, enable Google OAuth
- [ ] Verify each key with a one-line test script before proceeding

**Exit criteria:** `python test_keys.py` prints ✓ for Anthropic, Tavily, Supabase.

---

## Phase 1 — Agent Core (Days 2–4, ~8 hours)

**Goal:** `run_agent("Razorpay")` returns a complete dossier dict in the terminal, with ReAct steps printed to stdout.

### Step 1.1 — Tool Implementations

`backend/tools/search.py`
- [ ] `async def web_search(query: str) -> str`
- [ ] Call Tavily `/search` endpoint
- [ ] Return formatted string of top 5 results: `[1] Title\nURL\nSnippet\n---`
- [ ] Handle Tavily errors gracefully (return error string, don't raise)

`backend/tools/fetch.py`
- [ ] `async def fetch_page(url: str) -> str`
- [ ] Try Tavily Extract first (`/extract` endpoint)
- [ ] Fallback: httpx GET + BeautifulSoup4 text extraction (strip nav, footer, scripts)
- [ ] Hard limit: return max 4000 chars of content (context window hygiene)
- [ ] Blocklist: if domain is `linkedin.com` or `crunchbase.com`, skip direct fetch, return `"Direct scraping blocked for this domain. Use search result snippets instead."`

`backend/tools/dispatcher.py`
- [ ] `async def dispatch_tool(name: str, input: dict) -> str`
- [ ] Routes tool name → function, handles unknown tool gracefully

### Step 1.2 — System Prompt

`backend/agent/prompts.py`
- [ ] Write system prompt for ReAct agent:
  - Role: expert B2B company researcher
  - Goal: compile a full prospect dossier on `{company_name}`
  - Required fields: overview, industry, business model, HQ, founding year, headcount, funding, key people, recent news, talking points
  - Reasoning instruction: think before each tool call, explain why you're searching for what
  - Stopping instruction: call no more than 12 tools total; stop when all required fields have data or tool limit reached
  - Output instruction: when done, output a JSON object matching the dossier schema (no tool call, just text)

### Step 1.3 — ReAct Loop

`backend/agent/react_loop.py`
- [ ] `async def run_agent(company_name: str) -> dict`
- [ ] Message history management
- [ ] Tool call parsing from `response.content`
- [ ] Loop with `MAX_ITERATIONS = 12` guard
- [ ] Final synthesis: separate Sonnet call with accumulated context → structured JSON
- [ ] Print each step to stdout during development

### Step 1.4 — Test Run

- [ ] `python -m backend.agent.test_run "Razorpay"`
- [ ] Check dossier completeness: ≥ 6/8 fields populated
- [ ] Check iteration count: ≤ 12
- [ ] Check duration: < 120 seconds

**Exit criteria:** Full dossier JSON printed in terminal for "Razorpay" with ≥ 6 fields populated.

---

## Phase 2 — FastAPI Backend (Days 5–6, ~5 hours)

**Goal:** HTTP API with SSE streaming, dossier persistence, Clerk JWT validation.

### Step 2.1 — Job Queue

`backend/api/jobs.py`
- [ ] In-memory job store: `Dict[str, asyncio.Queue]`
- [ ] `create_job(company_name) → job_id`
- [ ] `get_job_queue(job_id) → Queue`
- [ ] Modify `run_agent()` to push events to queue instead of stdout

Event types to emit:
```python
{"type": "start", "company": company_name}
{"type": "reason", "text": "..."}         # LLM thinking (extract from text blocks)
{"type": "action", "tool": "web_search", "input": {"query": "..."}}
{"type": "observation", "tool": "web_search", "summary": "..."}
{"type": "complete", "dossier": {...}}
{"type": "error", "message": "..."}
```

### Step 2.2 — API Routes

`backend/api/routes/research.py`
- [ ] `POST /research` → create job, start `run_agent` as background task, return `{job_id}`
- [ ] `GET /research/{job_id}/stream` → SSE stream from queue
- [ ] `GET /research/{job_id}` → poll status (for non-SSE fallback)

`backend/api/routes/dossiers.py`
- [ ] `GET /dossiers` → fetch user's saved dossiers from Supabase (auth required)
- [ ] `GET /dossiers/{id}` → single dossier
- [ ] `DELETE /dossiers/{id}` → delete

### Step 2.3 — Supabase Integration

`backend/db/supabase.py`
- [ ] `async def save_dossier(user_id, company, dossier_json) → id`
- [ ] `async def get_dossiers(user_id) → list`
- [ ] `async def get_dossier(id, user_id) → dict`
- [ ] `async def delete_dossier(id, user_id)`
- [ ] Create the `dossiers` table + RLS policies (schema in TRD)
- [ ] Wire: on `complete` event, if `user_id` present, auto-save to Supabase

### Step 2.4 — Clerk Auth Middleware

`backend/api/middleware/auth.py`
- [ ] Extract `Authorization: Bearer <token>` header
- [ ] Verify JWT against Clerk JWKS endpoint
- [ ] Extract `user_id` from `sub` claim
- [ ] Attach to `request.state.user_id` (None if unauthenticated)
- [ ] `require_auth` dependency for protected routes

### Step 2.5 — Test API

- [ ] `curl -X POST localhost:8000/research -d '{"company": "Razorpay"}'`
- [ ] Open `localhost:8000/research/{id}/stream` in browser — see SSE events
- [ ] Verify dossier saved in Supabase after completion

**Exit criteria:** Full research job completes via HTTP, SSE events visible in browser network tab, dossier row appears in Supabase.

---

## Phase 3 — Frontend (Days 7–10, ~10 hours)

**Goal:** Functional multi-page React app. A user can type a company name, watch the ReAct stream live, and see the dossier rendered.

### Step 3.1 — Project Setup

- [ ] `npm create vite@latest frontend -- --template react`
- [ ] Install: `tailwindcss`, `@clerk/clerk-react`, `react-router-dom`, `lucide-react`
- [ ] Set up Tailwind config
- [ ] Set up Clerk provider in `main.jsx`
- [ ] Set up React Router with routes: `/`, `/research/:jobId`, `/history`, `/dossier/:id`

### Step 3.2 — Pages

**`/` — Home Page**
- [ ] Large centered input field: "Enter a company name"
- [ ] Submit button → POST `/research` → redirect to `/research/:jobId`
- [ ] If authenticated: show "X dossiers researched" stat

**`/research/:jobId` — Live Research Page**
- [ ] Connect to SSE: `GET /research/{jobId}/stream`
- [ ] Render ReAct steps as they arrive:
  - Reason steps: subtle grey text, italic
  - Action steps: highlight tool name + query in distinct color
  - Observation steps: dimmed summary text
- [ ] Progress bar or step counter (x/12 tool calls)
- [ ] On `complete` event: transition to dossier view (same page, below stream or replace)

**`/history` — Dossier History (auth required)**
- [ ] List of past dossiers: company name + date + quick summary
- [ ] Click → `/dossier/:id`
- [ ] Delete button per entry
- [ ] Empty state: "No dossiers yet. Research a company to get started."
- [ ] Redirect to `/` if unauthenticated

**`/dossier/:id` — Dossier Detail**
- [ ] Full rendered dossier from Supabase
- [ ] Same render component as live research page (reuse)

### Step 3.3 — Dossier Render Component

`components/DossierReport.jsx`
- [ ] Company name as hero heading
- [ ] Sections: Overview, Company Details (founding, HQ, headcount), Funding, Key People, Recent News, Talking Points
- [ ] Talking points: visually distinct callout boxes (these are the actionable output)
- [ ] Sources list at bottom: clickable links
- [ ] Agent metadata footer: iterations, duration, models used

### Step 3.4 — Auth UI

- [ ] `<SignInButton>` / `<UserButton>` from Clerk in navbar
- [ ] Soft gate: show "Sign in to save this dossier" banner on research complete if unauthenticated
- [ ] Don't block core feature behind login

**Exit criteria:** Full demo flow works — enter company name, watch stream, read dossier, sign in, check history.

---

## Phase 4 — Polish & Deploy (Days 11–13, ~5 hours)

### Step 4.1 — Error Handling

- [ ] Agent timeout (>90s): emit `error` event, show friendly UI message
- [ ] Tool failure: agent continues, marks field as "data unavailable"
- [ ] Partial dossier (< 6 fields): render what exists, label empty fields clearly
- [ ] SSE connection drop: auto-reconnect once, then show "connection lost" state
- [ ] Invalid company name (gibberish input): validate before submit

### Step 4.2 — Rate Limiting

- [ ] Backend: max 3 concurrent research jobs (in-memory semaphore)
- [ ] Per-IP: max 5 research runs/hour (simple dict, not Redis — good enough for portfolio)
- [ ] Show remaining runs in UI if near limit

### Step 4.3 — Deploy

**Backend → Render**
- [ ] Add `render.yaml` for Render free tier
- [ ] Set all env vars in Render dashboard
- [ ] Note: free tier sleeps after 15min inactivity — document this, add wakeup ping

**Frontend → Vercel**
- [ ] `vercel deploy` from `/frontend`
- [ ] Set `VITE_API_BASE_URL` and `VITE_CLERK_PUBLISHABLE_KEY`
- [ ] Update Clerk allowed origins to include Vercel domain
- [ ] Update CORS in FastAPI to allow Vercel domain

### Step 4.4 — README

- [ ] Animated GIF of live ReAct stream (record with Kap or LICEcap)
- [ ] One-line value prop at top
- [ ] Architecture diagram (copy from TRD)
- [ ] "Why raw tool use, no LangChain" section — this is the portfolio differentiator
- [ ] Setup instructions (10 minutes from clone to running)
- [ ] Link to live demo

---

## Summary Timeline

| Phase | Work | Est. Time |
|-------|------|-----------|
| 0 — Setup | Repo, env, API keys | 2 hours |
| 1 — Agent Core | Tools, ReAct loop, test | 8 hours |
| 2 — FastAPI | SSE, Supabase, Clerk auth | 5 hours |
| 3 — Frontend | 4 pages, stream, dossier UI | 10 hours |
| 4 — Polish + Deploy | Error handling, Render + Vercel | 5 hours |
| **Total** | | **~30 hours** |

Across 2 weeks at 2–3 hours/day, this is a realistic solo build.

---

## Build Order Warning

Don't do Phase 3 before Phase 1 is solid. The temptation to build the UI first is high. Resist it. A beautiful frontend streaming "Loading..." forever is not a portfolio piece.
