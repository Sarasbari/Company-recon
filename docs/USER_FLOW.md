# User Flow — company-recon
Version: 1.0 | Status: Draft

---

## Actors

- **Guest** — not signed in, can research but dossier not saved
- **Authenticated User** — signed in via Clerk, dossiers persisted to Supabase

---

## Flow 1 — Core Research (Guest)

```
[/] Home Page
    │
    ├── User types company name in input field
    │
    ├── [Validation]
    │     ├── Empty input → show inline error "Enter a company name"
    │     └── Valid input → enable Submit button
    │
    ├── User clicks Submit
    │
    ├── POST /research → returns job_id
    │
    ├── Redirect → [/research/:jobId] Live Research Page
    │
    ├── [SSE Stream connects]
    │     │
    │     ├── event: start    → show "Researching {company}..." header
    │     │
    │     ├── event: reason   → render reasoning step in stream log
    │     │
    │     ├── event: action   → render tool call (search query or URL)
    │     │
    │     ├── event: observe  → render observation summary
    │     │
    │     │   ... repeats up to 12 iterations ...
    │     │
    │     ├── event: complete → transition stream log to "done" state
    │     │                     render full dossier below (or replace stream)
    │     │
    │     └── event: error    → show error state with retry button
    │
    ├── [Dossier Rendered]
    │     │
    │     └── Show "Sign in to save this dossier" banner (soft gate)
    │           │
    │           └── User clicks Sign In → [Auth Flow] → return to same dossier
    │
    └── User reads dossier, copies talking points, done
```

---

## Flow 2 — Core Research (Authenticated User)

Same as Flow 1, with these differences:

```
    ├── POST /research includes Bearer token → job linked to user_id
    │
    ├── event: complete → dossier auto-saved to Supabase
    │                     no "sign in" banner; show "Saved to History ✓"
    │
    └── Navbar shows link to History
```

---

## Flow 3 — Auth Flow

```
User clicks "Sign In" (from navbar or dossier banner)
    │
    ├── Clerk modal opens (email/password or Google OAuth)
    │
    ├── On success → Clerk sets session token
    │
    └── User returned to previous page (research result or home)
```

---

## Flow 4 — History (Authenticated Only)

```
[/history] History Page
    │
    ├── [Not authenticated] → redirect to [/] with "Sign in to view history" toast
    │
    ├── [Authenticated] → GET /dossiers → render list
    │
    │     [Empty State]
    │     └── "No dossiers yet. Research a company to get started."
    │           └── CTA button → [/] Home
    │
    │     [Has Dossiers]
    │     ├── List items: Company Name | Date | "X talking points" tag
    │     │
    │     ├── Hover on list item → show mini-preview of overview
    │     │
    │     ├── Click list item → [/dossier/:id]
    │     │
    │     └── Delete icon on each item
    │           └── Confirm modal: "Delete Razorpay dossier? This can't be undone."
    │                 ├── Confirm → DELETE /dossiers/:id → remove from list
    │                 └── Cancel → dismiss modal
```

---

## Flow 5 — Dossier Detail (from History)

```
[/dossier/:id]
    │
    ├── GET /dossiers/:id → render dossier
    │
    ├── [Not found / not owned] → 404 state
    │
    ├── [Loading] → skeleton loader
    │
    └── [Loaded] → full dossier render
          │
          ├── "Research Again" button → back to [/] with company pre-filled
          │
          └── Delete button → confirm → DELETE → redirect to [/history]
```

---

## Flow 6 — Error States

```
Research Timeout (>90s)
    └── SSE error event: "Research took too long. Try a more specific company name."
          └── Retry button → new POST /research with same input

Tool Failures (partial data)
    └── Dossier renders with available fields
          └── Empty fields show: "Data unavailable — sources blocked or not found"
          └── Note at top: "Partial dossier — X of 8 fields populated"

Rate Limited
    └── POST /research returns 429
          └── UI shows: "You've run X researches this hour. Try again in Y minutes."

SSE Connection Drop
    └── Auto-reconnect once after 3 seconds
          └── If still disconnected: "Connection lost. Refresh to continue."

Invalid Input
    └── Client-side: trim + min 2 chars before submit
    └── Server-side: return 400 if company_name empty/too_short
```

---

## Page → Route Map

| Page | Route | Auth Required |
|------|-------|--------------|
| Home | `/` | No |
| Live Research | `/research/:jobId` | No |
| Dossier Detail (live + history) | `/dossier/:id` | Yes (history) |
| History | `/history` | Yes |
| Sign In / Sign Up | Clerk modal (no dedicated route) | — |

---

## State Transitions (Research Job)

```
pending → running → complete
                  ↘ failed
                  ↘ timeout
```

Stored in Supabase `dossiers.status` column. Frontend polls or uses SSE final event.
