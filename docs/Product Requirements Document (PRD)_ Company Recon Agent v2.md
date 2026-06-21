# Product Requirements Document (PRD): Company Recon Agent v2

## 1. Project Overview
Company Recon is an agentic B2B intelligence tool designed to perform deep, real-time research on companies. It uses a ReAct (Reasoning and Acting) loop to search the web, extract data, and synthesize a comprehensive "Prospect Dossier" for sales and research teams.

### 1.1 Goal
Transform the current prototype into a production-ready, high-fidelity agent that provides 100% accurate data, robust scraping capabilities, and a world-class real-time user experience.

---

## 2. Current Issues & Mistakes Identified

| Category | Issue Description | Impact |
| :--- | :--- | :--- |
| **Data Integrity** | Hardcoded mock data in `fetch.py` returns Razorpay info when API keys are missing. | Critical: "Zomato" research returns "Razorpay" data. |
| **Prompting** | Real-world company names used in prompt examples. | High: LLM "bleeding" or hallucinating based on examples. |
| **Scraping** | Basic BeautifulSoup fallback is easily blocked by modern sites. | Medium: Missing data for well-protected domains. |
| **Frontend** | Static log display instead of a live, animated reasoning stream. | Medium: Poor "Agentic" feel; user doesn't know what's happening. |
| **Testing** | No automated integration tests for the agent's research accuracy. | High: Regressions are hard to catch. |
| **Architecture** | Tight coupling between agent logic and tool implementations. | Low: Harder to swap tools (e.g., swapping Tavily for Firecrawl). |

---

## 3. Functional Requirements

### 3.1 Agent Core (The "Brain")
*   **Zero-Knowledge Synthesis**: Remove all real-company examples from prompts. Use abstract schemas.
*   **Cross-Source Validation**: The agent must compare data from at least 2 different sources before finalizing a field (e.g., funding).
*   **Source Attribution**: Every piece of data in the final dossier must be linked to a specific source URL.
*   **Self-Correction**: If the agent detects a "Blocked" or "Empty" response, it must automatically try an alternative search query.

### 3.2 Tooling & Scraping
*   **Robust Fetcher**: Integrate a professional scraping proxy or service (e.g., Firecrawl, Jina, or Bright Data) to handle LinkedIn/Crunchbase snippets.
*   **No-Mock Policy**: Remove all hardcoded data. If an API key is missing, the system should fail gracefully with a "Configuration Error" rather than returning fake data.
*   **File Analysis**: Ability to "read" PDF reports if found during search (e.g., annual reports).

### 3.3 Frontend & UX
*   **Live Reasoning Stream**: 
    *   Real-time SSE (Server-Sent Events) consumption.
    *   Animated "Thought" blocks showing the agent's internal monologue.
    *   Monospace "Action" chips for search queries and URL fetches.
*   **Interactive Dossier**: 
    *   Progressive loading: sections populate as the agent finds data.
    *   "Verify" buttons next to data points that link to the source.
    *   Export to PDF/Markdown functionality.
*   **History & Comparison**: Ability to compare two dossiers side-by-side.

---

## 4. Technical Requirements

### 4.1 Backend (FastAPI + Python)
*   **Type Safety**: Implement Pydantic models for all tool inputs/outputs and final dossiers.
*   **Asynchronous Processing**: Ensure the ReAct loop is fully non-blocking.
*   **Logging**: Implement structured logging (e.g., Loguru) to track agent trajectories for debugging.

### 4.2 Frontend (React + Tailwind 4)
*   **State Management**: Optimize React 19 hooks for handling high-frequency SSE updates.
*   **Animations**: Use Framer Motion or CSS transitions for the " fadeInUp" effect on log entries.
*   **Auth**: Fully integrate Clerk for user management and persistent history.

### 4.3 Database (Supabase)
*   **Schema**: Store not just the final dossier, but the full "Trajectory" (steps taken) for every job.

---

## 5. Success Metrics
1.  **Accuracy**: 0% "Razorpay" data leakage in non-Razorpay searches.
2.  **Latency**: Average dossier generation under 45 seconds.
3.  **Reliability**: 95% success rate in extracting funding data for Series A+ startups.

---

1. **LLM Strategy**: I will refactor the backend to use a provider-agnostic approach (supporting Groq or Gemini for their generous free tiers), while ensuring the code is high-quality and robust.
2. **Multi-Source Validation**: I will implement logic where the agent cross-references data points across multiple search results before finalizing them in the dossier.
3. **Free Scraping**: I will integrate Jina Reader and Firecrawl (free tier) to replace the current basic BeautifulSoup fallback.
4. **Production Readiness**: I will prepare the repo for deployment on Vercel (Frontend) and Render (Backend), including necessary configuration files (vercel.json, render.yaml, etc.).
