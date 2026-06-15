# TRD — company-recon
**Technical Requirements Document**
Version: 1.0 | Status: Draft

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│   React 18 + Vite + Tailwind CSS                           │
│   Pages: Home / Research / History / Dossier Detail        │
│   Clerk SDK (auth state, session token)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP + SSE
┌──────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                      │
│                                                             │
│  POST /research          → kick off agent job               │
│  GET  /research/{id}/stream → SSE stream of ReAct steps    │
│  GET  /dossiers          → user's history (auth required)   │
│  GET  /dossiers/{id}     → single dossier                   │
│  DELETE /dossiers/{id}   → delete entry                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ReAct Agent Engine                     │   │
│  │                                                     │   │
│  │  run_agent(company_name)                            │   │
│  │    → build system prompt + tool definitions         │   │
│  │    → LLM call → parse tool_use response             │   │
│  │    → dispatch tool → append observation             │   │
│  │    → repeat (max 12 iterations)                     │   │
│  │    → final synthesis call → structured dossier JSON │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Tools: web_search() | fetch_page()                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  Anthropic API   Tavily API     Supabase
  (claude-haiku)  (search+extract) (postgres)
```

---

## 2. Tech Stack

| Layer | Choice | Justification |
|-------|--------|---------------|
| LLM | `claude-haiku-4-5` for ReAct loop, `claude-sonnet-4-6` for final synthesis | Haiku is ~20x cheaper per token; Sonnet only used once per job for quality dossier output |
| Search | Tavily Search API + Tavily Extract | Search for discovery; Extract for page content (bypasses bot blocks that would kill raw httpx on Crunchbase/LinkedIn) |
| Scraping | httpx + BeautifulSoup4 | Fallback only when Tavily Extract fails or URL is a simple static page |
| Backend | FastAPI + Python 3.11 | Async-native, SSE support, fast iteration |
| Auth | Clerk (Python SDK backend + React SDK frontend) | JWT verification on FastAPI; first-time use for portfolio learning |
| Database | Supabase (PostgreSQL) | Already familiar; RLS for per-user dossier isolation |
| Frontend | React 18 + Vite + Tailwind CSS | Known stack; Vite for fast dev |
| Deploy | Vercel (frontend) + Render free tier (backend) | Both free; sufficient for portfolio traffic |

---

## 3. Tool Definitions (Claude Tool Use)

Only 2 real tools. Extraction and compilation are LLM reasoning — not tool calls.

### 3.1 `web_search`
```json
{
  "name": "web_search",
  "description": "Search the web for information about a company. Use specific queries. Prefer queries like 'Razorpay funding 2024 Crunchbase' over 'Razorpay'. Returns top 5 results with title, URL, and snippet.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The search query. Be specific. Include company name + topic."
      }
    },
    "required": ["query"]
  }
}
```

### 3.2 `fetch_page`
```json
{
  "name": "fetch_page",
  "description": "Fetch and extract readable text content from a URL. Use for official company websites, press releases, news articles. Do NOT use for LinkedIn or Crunchbase direct pages — they block scrapers. Prefer Tavily Extract for those.",
  "input_schema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "The full URL to fetch."
      }
    },
    "required": ["url"]
  }
}
```

**Why no `extract_structured_data` or `compile_dossier` tools?** These are LLM reasoning steps, not external side effects. Wrapping them as tool calls wastes a full round-trip to Anthropic. The final synthesis is a direct LLM call with a structured output prompt.

---

## 4. ReAct Loop Implementation

```python
# agent/react_loop.py

MAX_ITERATIONS = 12
TIMEOUT_SECONDS = 90

async def run_agent(company_name: str, job_id: str, queue: asyncio.Queue):
    messages = []
    system_prompt = build_system_prompt(company_name)
    tools = [WEB_SEARCH_TOOL, FETCH_PAGE_TOOL]
    iteration = 0

    while iteration < MAX_ITERATIONS:
        # LLM call
        response = anthropic.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Check stop condition
        if response.stop_reason == "end_turn":
            # LLM decided it has enough data — break
            break

        if response.stop_reason == "tool_use":
            tool_calls = [b for b in response.content if b.type == "tool_use"]

            for tool_call in tool_calls:
                # Stream the action to frontend
                await queue.put({
                    "type": "action",
                    "tool": tool_call.name,
                    "input": tool_call.input
                })

                # Execute tool
                result = await dispatch_tool(tool_call.name, tool_call.input)

                # Stream observation
                await queue.put({
                    "type": "observation",
                    "tool": tool_call.name,
                    "summary": result[:300]  # truncated for stream
                })

                # Append to message history
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call.id,
                        "content": result
                    }]
                })

        iteration += 1

    # Final synthesis — use Sonnet for quality
    dossier = await synthesize_dossier(company_name, messages)
    await queue.put({"type": "complete", "dossier": dossier})
```

---

## 5. SSE Streaming

```python
# api/routes/research.py

@router.get("/research/{job_id}/stream")
async def stream_research(job_id: str):
    async def event_generator():
        queue = job_queues[job_id]
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event["type"] == "complete":
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

Frontend consumes with `EventSource` or `fetch` + `ReadableStream`.

---

## 6. Database Schema (Supabase)

```sql
-- users table managed by Clerk, referenced by clerk_user_id

create table dossiers (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,           -- Clerk user ID
  company     text not null,
  status      text default 'pending',  -- pending | running | complete | failed
  dossier     jsonb,                   -- full structured output
  token_usage jsonb,                   -- {input_tokens, output_tokens, estimated_cost}
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- RLS: users can only read/delete their own rows
alter table dossiers enable row level security;

create policy "users_own_dossiers" on dossiers
  for all using (user_id = auth.jwt() ->> 'sub');
```

> **Note:** Clerk's JWT `sub` claim is the Clerk user ID. Configure Supabase JWT secret to match Clerk's JWKS endpoint.

---

## 7. Dossier JSON Schema

```json
{
  "company": "Razorpay",
  "researched_at": "2025-06-14T10:30:00Z",
  "overview": "string (1-2 paragraphs)",
  "industry": "string",
  "business_model": "string",
  "founded": "2014",
  "headquarters": "Bengaluru, India",
  "headcount": "1001-5000 (estimated)",
  "funding": {
    "stage": "Series F",
    "total_raised": "$741.5M",
    "last_round": "$375M (2021)",
    "investors": ["GIC", "Lone Pine Capital", "Tiger Global"]
  },
  "key_people": [
    { "name": "Harshil Mathur", "role": "CEO & Co-founder" },
    { "name": "Shashank Kumar", "role": "CTO & Co-founder" }
  ],
  "recent_news": [
    {
      "title": "string",
      "url": "string",
      "date": "string",
      "summary": "string"
    }
  ],
  "talking_points": [
    "string",
    "string",
    "string"
  ],
  "sources": ["url1", "url2"],
  "agent_metadata": {
    "iterations": 8,
    "tool_calls": 9,
    "duration_seconds": 47,
    "model_used": "claude-haiku-4-5 + claude-sonnet-4-6"
  }
}
```

---

## 8. API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/research` | Optional | Start a research job. Returns `job_id` |
| GET | `/research/{job_id}/stream` | Optional | SSE stream of ReAct steps |
| GET | `/research/{job_id}` | Optional | Poll job status + dossier when complete |
| GET | `/dossiers` | Required | List user's saved dossiers |
| GET | `/dossiers/{id}` | Required | Get single saved dossier |
| DELETE | `/dossiers/{id}` | Required | Delete a dossier |

---

## 9. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Research job completion | < 120 seconds (p90) |
| SSE first event latency | < 3 seconds from submit |
| Frontend bundle size | < 500KB gzipped |
| API cold start (Render) | < 8 seconds (documented in README) |
| Supabase RLS enforced | All dossier queries server-side validated |
| Error states handled | Timeout, partial data, tool failure — all surface in UI |

---

## 10. Environment Variables

```env
# Backend
ANTHROPIC_API_KEY=
TAVILY_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=

# Frontend
VITE_API_BASE_URL=
VITE_CLERK_PUBLISHABLE_KEY=
```
