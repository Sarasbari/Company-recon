# V2 Improvement Plan — company-recon
Version: 2.0 | Status: Draft — pending answers to diagnostic questions

---

## 0. Root Cause Analysis (Critical — blocks everything else)

**Symptom:** Searching "Zomato" returns Razorpay's profile, verbatim, matching a placeholder example from the project's own TRD.

**This is a P0 bug, not a polish item.** A dossier tool that returns wrong company data is worse than no tool — it actively misleads whoever uses it for outreach. Nothing in Phase B/C/D matters until this is closed.

**Most likely causes, in order of probability:**

1. Synthesis prompt contains a few-shot example dossier that's specific enough for the model to pattern-match and regurgitate when real tool-call context is thin, missing, or malformed.
2. Job state bug — `job_id` keying or in-memory queue returns a stale/previous job's result regardless of new input.
3. Leftover hardcoded test fixture sitting in place of the real `synthesize_dossier()` call from initial scaffolding.

**Fix requires, regardless of which cause it is:**

- [ ] Remove any literal example dossier content from prompts — replace with an abstract schema description (field names + types only, zero real company data, zero recognizable phrasing)
- [ ] Add an assertion/test: log the company name passed into `synthesize_dossier()` and the company name appearing in the *output* JSON. If they don't match exactly, fail loudly (raise, don't silently return)
- [ ] Add an integration test: run the full pipeline for 3 distinct companies (e.g. Zomato, Stripe, Tata Motors) in the same test session and assert each output's `company` field and `industry` field are distinct and correct. This is the regression test that would have caught this bug before it reached a screenshot.
- [ ] Log raw Tavily search results to a file/console for each run during debugging — confirm real "Zomato" data is actually returned by the search API before blaming the LLM
- [ ] Search the codebase for any string match on "Razorpay", "741.5M", or "developer-friendly APIs" — if any hit outside of docs/, that's your hardcoded fixture

---

## 1. Scraping & Data Quality — "Scrape like a pro"

Current state (inferred from symptom): scraping either isn't running, isn't being passed to synthesis, or isn't robust enough to return usable signal.

### 1.1 Multi-layer fetch strategy

Don't rely on one method per URL. Chain fallbacks:

```
1. Tavily Extract (handles JS-rendered pages, bypasses basic bot detection)
2. httpx + BeautifulSoup4 (static HTML fallback)
3. If both fail on a domain known to block scrapers (LinkedIn, Crunchbase,
   Glassdoor) → skip fetch entirely, rely on Tavily SEARCH result snippets only
```

- [ ] Implement `fetch_with_fallback(url)` that tries Extract first, catches failure, tries httpx+BS4, catches failure, returns `None` with a logged reason (never silently return empty string — that's indistinguishable from "no content found" downstream)
- [ ] Maintain a `BLOCKED_DOMAINS` list (linkedin.com, crunchbase.com if extract fails, glassdoor.com) — for these, instruct the agent in the system prompt to rely on search snippets, never attempt direct fetch

### 1.2 Query quality

- [ ] Audit the actual search queries your agent generates mid-run (log them). Vague queries like `"Zomato"` alone return generic/wrong-context results. The system prompt should explicitly instruct: always include a qualifier — `"Zomato company overview business model"`, `"Zomato funding history Crunchbase"`, `"Zomato CEO leadership team"` — never bare company name.
- [ ] Add disambiguation handling: many company names collide (e.g. multiple companies named "Wave," "Stripe" the payment co. vs other Stripes). System prompt should instruct the agent to verify the first search result's snippet actually describes a company matching context clues (industry hints from the user's original input) before proceeding.

### 1.3 Source quality scoring

- [ ] Tag each piece of extracted data with its source URL and a basic trust tier: official site / major news outlet / Crunchbase-class data aggregator / unverified blog. Surface this in the dossier UI (sources section) so the user can judge reliability — don't present everything with equal confidence.

### 1.4 Rate limit & retry handling

- [ ] Wrap Tavily calls in exponential backoff retry (2 attempts, 1s/2s delay) for transient failures
- [ ] If Tavily monthly quota is exhausted, fail with a clear UI error, not a silent fallback to hallucinated data

---

## 2. System Logic Improvements

### 2.1 Observability

- [ ] Structured logging for every agent run: `job_id`, `company_name`, every tool call + input + output length, final token usage, total duration. Write to a local file or simple table — you need this to debug the *next* version of this bug, not just this one.
- [ ] Add a `/debug/{job_id}` endpoint (dev-only, gated) that returns the full raw message history for a completed job — lets you inspect exactly what the LLM saw before it produced output.

### 2.2 Validation layer between agent output and dossier render

- [ ] Before saving/rendering a dossier, run a cheap validation pass: does `dossier.company` match the requested company name (case-insensitive, fuzzy match allowed for minor formatting)? If not, reject and retry once before surfacing an error to the user. This is a backstop in case the prompt fix in Section 0 doesn't fully eliminate drift.

### 2.3 Idempotency / job state

- [ ] Confirm each `job_id` is UUID-generated per request, not reused. Confirm the in-memory queue/dict is cleared after each job completes (memory leak + stale-data risk otherwise).

### 2.4 Partial data handling

- [ ] If a field can't be populated after exhausting search attempts, the dossier should explicitly say `"data_unavailable": true` for that field rather than the LLM inventing a plausible-sounding value. This needs to be an explicit instruction in the synthesis prompt: "If you don't have verified information for a field, mark it unavailable. Do not guess or use example data."

---

## 3. UI/UX Rebuild

Per the original UI/UX brief, the live stream is supposed to be the product's signature moment. Your current screenshot shows a static "Agent Logs" summary box (status/tool calls/time) — no live reasoning, no color-coded steps, no real-time feel. That's the biggest gap between what was speced and what's built.

### 3.1 Live stream log (the actual feature, not a summary)

- [ ] Wire the frontend to consume SSE events in real time, not just display a final summary. Each event type renders immediately as it arrives:
  - `reason` → italic grey text
  - `action` (search) → blue monospace chip with the literal query
  - `action` (fetch) → purple monospace chip with the literal URL
  - `observe` → green-bordered 2-3 sentence summary
- [ ] "Expand Log" should default to *expanded* during an active run — collapsing live reasoning behind a click defeats the purpose of building it
- [ ] Auto-scroll the log container as new events arrive

### 3.2 Category/tag correctness

- [ ] The "Fintech / Financial Services" tag under ZOMATO is wrong (Zomato is food delivery/quick commerce) — this will self-correct once Section 0's bug is fixed, but add it as a manual QA checkpoint: spot-check the industry tag against ground truth for every test run.

### 3.3 Animations (per brief — minimal, deliberate)

- [ ] Stream entries: `fadeInUp`, 150ms ease-out, as each event renders
- [ ] Dossier sections: `fadeIn`, 200ms, as each section populates with real data (progressive reveal, not all-at-once after a spinner)
- [ ] "Research complete" banner: one subtle pulse, not a loop
- [ ] No scroll-triggered card animations, no hover-scale effects — these read as templated

### 3.4 Talking points hierarchy

- [ ] Confirm talking points render with the amber-accent card treatment from the brief — they're the actual deliverable a user copies into an email. If they're currently rendering with the same visual weight as "Company Details," that's a hierarchy miss.

---

## 4. QA / Eval Suite (do this before calling V2 "done")

- [ ] Build a test script that runs the full pipeline against 5 known companies spanning different industries: Zomato (food delivery), Stripe (fintech), Tata Motors (manufacturing), Notion (SaaS), and one company with a name collision risk (e.g. "Wave")
- [ ] For each, manually verify: correct industry, correct HQ, correct founding year, no cross-contamination between runs
- [ ] Run them in the same session back-to-back (not isolated restarts) — this is what would have caught the original bug, since cross-job contamination is a session-state issue

---

## Priority Order

| Priority | Item | Why first |
|----------|------|-----------|
| P0 | Section 0 — root cause fix + regression test | Tool is actively wrong without this |
| P1 | Section 2.2 — validation backstop | Cheap insurance against recurrence |
| P1 | Section 1.1/1.2 — fetch fallback + query quality | Determines whether dossiers have real signal |
| P2 | Section 3.1 — live stream wiring | Core demo differentiator, currently missing |
| P2 | Section 4 — eval suite | Prevents shipping the next version of this bug |
| P3 | Section 3.3 — animations | Polish, do last |

---

## Antigravity Prompt

Paste this into Antigravity (or Cursor) as a single task. It's written to force diagnosis before code changes, since blind fixing without confirming root cause risks patching the wrong layer.

```
You are debugging and improving an existing agentic project called company-recon.
A ReAct-loop research agent (Claude API + Tavily) is returning WRONG data: when
researching "Zomato" (a food delivery company), the output dossier is an exact
match for "Razorpay" (a fintech company) — same industry tag, same funding numbers,
same business description. This is a data integrity bug, not a cosmetic issue.

STEP 1 — DIAGNOSE FIRST. Do not change code yet. Investigate and report findings on:
  a) Does the system prompt or any prompt template contain a literal example
     dossier with real company data (especially anything mentioning Razorpay,
     "$741.5M", "developer-friendly APIs", or "Series F")? If found, this is
     likely bleeding into model output via pattern-matching.
  b) Trace the actual function that produces the final dossier JSON. Confirm:
     does it receive the full accumulated tool-call results (search/fetch
     outputs) in its context, or is it called with insufficient/empty context?
  c) Check for job_id / cache key collisions — is there any chance results
     from a previous run are being returned for a new request?
  d) Search the entire codebase for any hardcoded/mock dossier fixture that
     might still be wired into the live code path instead of the real LLM call.
  e) Add temporary logging to print: the company name passed in, every search
     query generated, the raw search results returned, and the company name
     in the final output. Run it once for "Zomato" and report what you see
     at each stage before proceeding.

STEP 2 — FIX based on what STEP 1 reveals. Likely required changes:
  - Remove any real-company example data from prompts; replace with an
    abstract schema-only description (field names and types, no real values)
  - Add an explicit instruction in the synthesis prompt: "Only use information
    found via tool calls in this conversation. Never use prior knowledge about
    other companies. If a field is unverifiable, mark it explicitly as
    unavailable rather than guessing."
  - Add a post-generation validation check: assert the company name in the
    output JSON matches the requested company name (fuzzy match ok). If
    mismatch, retry once, then surface an error rather than returning bad data.

STEP 3 — REGRESSION TEST. Write an integration test that runs the full
pipeline for 3 different companies in the same process (Zomato, Stripe, Tata
Motors) and asserts each output has the correct, distinct industry and
business description. This test must fail on the current code and pass after
your fix.

STEP 4 — SCRAPING ROBUSTNESS. Improve fetch_page to:
  - Try Tavily Extract first, fall back to httpx+BeautifulSoup4 on failure
  - Skip direct fetch entirely for linkedin.com and crunchbase.com (these
    block scrapers) — rely on Tavily search result snippets instead for
    those domains
  - Never return an empty string silently on failure — return a clearly
    marked failure reason that the agent can reason about

STEP 5 — LIVE STREAM UI. The frontend currently shows a static post-completion
summary box ("Agent Logs: status/tool calls/time") instead of a live, real-time
reasoning stream. Fix this:
  - Consume the SSE stream and render each event AS IT ARRIVES, not after
    completion
  - Color-code by event type: reasoning steps in muted italic grey, search
    actions in blue monospace chips showing the literal query, fetch actions
    in purple monospace chips showing the literal URL, observations in
    green-bordered short summaries
  - Default the log to expanded during an active run
  - Add fadeInUp animation (150ms ease-out) per new log entry, and fadeIn
    (200ms) as dossier sections populate progressively with real data

Report back what STEP 1 found before making changes in STEP 2 onward — I want
to confirm the root cause diagnosis before you touch the synthesis prompt or
the data pipeline.
```
