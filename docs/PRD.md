# PRD — company-recon
**Product Requirements Document**
Version: 1.0 | Status: Draft

---

## 1. Problem Statement

Sales reps, founders, and recruiters spend 20–40 minutes manually researching a company before an outreach call — Googling, checking Crunchbase, LinkedIn, and news sites, then copy-pasting into a doc. The output is inconsistent, often outdated, and non-reusable.

`company-recon` eliminates that prep work. Input a company name, get a structured, sourced dossier in under 2 minutes — automatically.

---

## 2. Target Users

**Primary (portfolio demo audience)**
- Technical recruiters evaluating Saras's AI/ML engineering skills
- Hackathon judges assessing agentic system design

**Secondary (real usage post-deploy)**
- Early-stage sales reps doing pre-call research
- Founders vetting potential partners or investors
- Freelancers qualifying leads before pitching

---

## 3. Goals

| Goal | Metric |
|------|--------|
| Research time under 2 minutes | Measured from submit → dossier rendered |
| Dossier completeness | ≥ 6 of 8 fields populated per run |
| Agent loop efficiency | ≤ 12 tool calls per research job |
| Retention | Returning users check history within same session |

---

## 4. Non-Goals (V1)

- No CRM integration (HubSpot, Salesforce)
- No bulk/batch company research
- No email draft generation from dossier
- No real-time monitoring / alerts
- No team/org accounts (single user per Clerk account)

---

## 5. Feature Scope

### V1 — Core (build this first)

**5.1 Research Input**
- Single text input: company name (± website URL as optional hint)
- Submit triggers agent job, input locked until complete
- Visual indicator: job queued → running → complete

**5.2 Live ReAct Stream**
- SSE stream from FastAPI → React UI
- Each agent step rendered as it happens:
  - `[REASON]` — LLM thinking (truncated to 1–2 sentences)
  - `[SEARCH]` — query string being searched
  - `[FETCH]` — URL being scraped
  - `[OBSERVE]` — brief summary of what was found
- This is the primary wow-factor for portfolio demos — do not cut it

**5.3 Dossier Output**
Structured report rendered from JSON. Minimum fields:

| Field | Source Strategy |
|-------|----------------|
| Company overview (1 para) | Web search + fetch homepage |
| Industry & business model | Web search + extract |
| Founding year & HQ location | Web search |
| Headcount estimate | LinkedIn / Crunchbase search result snippets |
| Funding stage & total raised | Crunchbase search snippets (not direct scrape) |
| Key people (CEO, CTO, founders) | Web search |
| Recent news (last 90 days, top 3) | Tavily news search |
| Talking points (3 bullets) | LLM synthesized from all above |

**5.4 Dossier History (requires Supabase)**
- Authenticated users see past dossiers in sidebar
- Each entry: company name, timestamp, quick-view on hover
- Max 50 stored per user (free tier constraint)
- Delete individual entries

**5.5 Auth (Clerk)**
- Email/password + Google OAuth via Clerk
- Unauthenticated users: can run research but dossier not saved
- Authenticated: history persisted to Supabase
- Auth gate is soft — don't block the core feature behind login

### V2 — Post-launch

- Export dossier as PDF
- Shareable dossier link (public URL, no auth required)
- Confidence score per dossier field
- Retry failed fields individually
- Bulk input (CSV of company names)

---

## 6. User Stories

```
As a sales rep, I want to type a company name and get a dossier
so that I don't spend 30 minutes Googling before a call.

As a returning user, I want to see my past researches
so that I don't re-run the same company twice.

As a demo viewer (recruiter/judge), I want to watch the agent
reason and search in real time so I understand how it works.

As a user on mobile, I want the dossier to be readable
without horizontal scroll.
```

---

## 7. Constraints & Risks

| Constraint | Impact | Mitigation |
|-----------|--------|-----------|
| Tavily free tier: 1000 searches/month | ~100–200 research runs/month max | Rate limit per user; show usage counter in UI |
| Claude API: no free tier | ~$0.01–0.03 per run (Haiku) | Cheap enough; add $5 credit; show cost estimate in README |
| Crunchbase/LinkedIn block scrapers | Funding/people data will be incomplete sometimes | Use Tavily search result snippets instead of direct page fetch; mark fields as "estimated" |
| ReAct loop can spiral | Wasted tokens + slow response | Hard cap: 12 tool calls max; 90s timeout on job |
| SSE on Render free tier sleeps after 15min | Cold start kills demo | Ping endpoint in README instructions; note in UI |

---

## 8. Success Definition

A successful V1 is: a deployed URL, a working demo with a real company (e.g. "Razorpay"), a live ReAct stream, a rendered dossier, and a history page — all functional in a 3-minute walkthrough video for portfolio/internship applications.
