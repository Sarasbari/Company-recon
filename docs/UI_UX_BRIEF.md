# UI/UX Brief — company-recon
Version: 1.0 | Status: Draft

---

## Design Direction

`company-recon` is an intelligence tool, not a consumer app. The design should feel like a Bloomberg terminal met a modern SaaS product — data-dense, high signal, no decorative noise. The user's job is to read and act fast. The UI's job is to get out of the way.

The signature moment is the **live ReAct stream** — watching an AI reason, search, and piece together intelligence in real time. That's the product's core drama and the design should frame it as such, not bury it in chrome.

---

## Visual Identity

### Color Palette

```
Background (primary)    #0A0A0F   Near-black, slight blue undertone
Background (surface)    #111118   Cards, panels
Background (elevated)   #1A1A24   Modals, hover states
Border                  #2A2A38   Subtle separators

Text (primary)          #F0F0F8   High contrast white-grey
Text (secondary)        #7A7A9A   Labels, metadata, timestamps
Text (muted)            #4A4A66   Disabled, placeholders

Accent (blue)           #4F7EFF   Primary actions, links
Accent (green)          #3ECFA0   Success, "complete", savings/positive
Accent (amber)          #F5A623   Warnings, partial data flags
Accent (red)            #FF4F4F   Errors, delete

Stream colors:
  REASON step           #7A7A9A   Italic, muted — thinking is quiet
  ACTION step           #4F7EFF   Highlighted — tool call is decisive
  OBSERVE step          #3ECFA0   Subtle green — data received
```

### Typography

```
Display face:   "Space Grotesk" (Google Fonts)
                — Used for company name, page headings, dossier title
                — Geometric, technical, slightly cold — fits the intel feel

Body face:      "Inter" (Google Fonts)
                — All body copy, dossier content, descriptions

Monospace:      "JetBrains Mono" (Google Fonts)
                — ReAct stream log, tool call inputs (queries, URLs), metadata
                — This is the key typographic differentiator — mono for the agent layer

Type scale:
  xs:   11px / 1.4    Metadata, source URLs
  sm:   13px / 1.5    Labels, stream observations
  base: 15px / 1.6    Body copy, dossier paragraphs
  lg:   18px / 1.4    Section headings
  xl:   24px / 1.3    Page title, company name
  2xl:  36px / 1.1    Hero company name in dossier header
```

### Spacing & Shape

```
Radius:         6px for cards, 4px for inputs, 2px for tags — minimal, sharp
Grid:           12-column, max-width 1200px, centered
Card padding:   24px desktop / 16px mobile
Section gap:    32px
```

---

## Pages

### Page 1 — Home `/`

**Layout:** Single centered column, vertically centered in viewport

```
┌─────────────────────────────────────┐
│  NAVBAR: logo | [History] [Sign In] │
├─────────────────────────────────────┤
│                                     │
│         company-recon               │  ← Space Grotesk, 36px
│   Prospect intelligence, automated  │  ← Inter, muted, 15px
│                                     │
│  ┌──────────────────────────────┐   │
│  │  Company name or website URL │   │  ← input, full width, 48px tall
│  └──────────────────────────────┘   │
│                [Research →]         │  ← primary button
│                                     │
│  ── Try: Razorpay · Stripe · Zomato │  ← clickable suggestions, muted
│                                     │
│  [Auth user only]                   │
│  You've researched 12 companies     │  ← small stat, very muted
│                                     │
└─────────────────────────────────────┘
```

**Interactions:**
- Input: focused by default on page load
- Enter key submits
- Suggestion chips: click to populate input + auto-submit
- If authenticated + has history: show stat

---

### Page 2 — Live Research `/research/:jobId`

**Layout:** Two-column on desktop (stream left, dossier right after complete). Single column on mobile (stream stacked above dossier).

```
DESKTOP (during stream):
┌──────────────────────┬──────────────────────────┐
│  STREAM LOG          │  DOSSIER PREVIEW          │
│  ─────────────────   │  ───────────────────────  │
│                      │                           │
│  [REASONING]         │  ┌─────────────────────┐  │
│  I need to find      │  │ Razorpay            │  │
│  company overview    │  │ Researching...      │  │
│  and funding...      │  │                     │  │
│                      │  │ ■■■□□□□□ 3/12 tools │  │
│  [SEARCH]            │  │                     │  │
│  "Razorpay company   │  │ Overview        ...  │  │
│   overview 2024"     │  │ Funding         ...  │  │
│                      │  │ Key People      ...  │  │
│  [OBSERVE]           │  │ News            ...  │  │
│  Found: company was  │  └─────────────────────┘  │
│  founded in 2014...  │                           │
│                      │  Fields populate as data  │
│  [SEARCH]            │  arrives (not all at end) │
│  "Razorpay Series F  │                           │
│   funding round"     │                           │
└──────────────────────┴──────────────────────────┘
```

**Stream Log Rendering:**

Each event type has a distinct visual treatment:
```
[REASONING]  — no label, italic grey text, small, no border
              "Considering whether to fetch the homepage for product info..."

[SEARCH]     — monospace chip with magnifier icon, blue tint background
              🔍  "Razorpay funding Series F 2024"

[FETCH]      — monospace chip with link icon, purple tint
              🔗  crunchbase.com/organization/razorpay

[OBSERVE]    — small paragraph, green left border, 2-3 sentences max
              ✓ Found founding year (2014), HQ (Bengaluru), CEO (Harshil Mathur)

[COMPLETE]   — full-width banner: "Research complete — 47s · 9 tool calls"
```

**On Complete:**
- Stream log collapses to summary bar (shows step count + duration, expandable)
- Full dossier renders in right column (or replaces stream on mobile)
- If authenticated: "Saved to History ✓" badge
- If guest: "Sign in to save this dossier" banner (dismissable)

---

### Page 3 — Dossier View (inline on research page, or `/dossier/:id`)

```
┌─────────────────────────────────────────────────────────┐
│  RAZORPAY                               [Research Again] │  ← 2xl display
│  Fintech · Bengaluru, India · Founded 2014              │  ← metadata row
├─────────────────────────────────────────────────────────┤
│  OVERVIEW                                               │
│  Razorpay is India's leading payment solutions company...│
│                                                         │
├───────────────────────┬─────────────────────────────────┤
│  COMPANY DETAILS      │  FUNDING                        │
│  Industry: Fintech    │  Stage: Series F                │
│  HQ: Bengaluru        │  Total: $741.5M                 │
│  Headcount: 1K–5K     │  Last: $375M (2021)             │
│  Founded: 2014        │  Investors: GIC, Tiger Global   │
├───────────────────────┴─────────────────────────────────┤
│  KEY PEOPLE                                             │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ Harshil Mathur   │  │ Shashank Kumar   │            │
│  │ CEO & Co-founder │  │ CTO & Co-founder │            │
│  └──────────────────┘  └──────────────────┘            │
├─────────────────────────────────────────────────────────┤
│  RECENT NEWS                                            │
│  · Razorpay launches PayOut Links for B2B payments      │
│    TechCrunch · 3 days ago                              │
│  · ...                                                  │
├─────────────────────────────────────────────────────────┤
│  ★ TALKING POINTS                         ← amber accent│
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Razorpay's recent expansion into Southeast Asia    │ │
│  │ aligns with your company's APAC growth goals...   │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ They've scaled from startup to 1000+ employees in  │ │
│  │ 10 years — they understand growth infrastructure  │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Series F with Tiger Global signals they're         │ │
│  │ preparing for IPO — urgency may be a lever...     │ │
│  └────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  SOURCES  · crunchbase.com  · techcrunch.com  · +3      │
│  Generated in 47s · 9 tool calls · Haiku + Sonnet      │  ← muted footer
└─────────────────────────────────────────────────────────┘
```

**Talking Points** are the hero output — make them the most visually distinct element. These are what users actually use in their outreach.

---

### Page 4 — History `/history`

```
┌─────────────────────────────────────────────────────────┐
│  Research History                         [+ Research]  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐   │
│  │  RAZORPAY            Fintech · Jun 14, 2025  [×] │   │
│  │  "Series F, $741.5M raised, expanding to SEA..." │   │  ← hover preview
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  STRIPE              Fintech · Jun 12, 2025  [×] │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ZOMATO              FoodTech · Jun 10, 2025 [×] │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Navbar

```
company-recon [logo]             [History]  [Sign In / UserButton]
```

- Logo: text-based, "company-recon" in Space Grotesk, accent blue dot as logo mark
- Sticky, height 56px
- History link: only shown if authenticated
- UserButton: Clerk's built-in component (avatar + dropdown)
- Mobile: hamburger collapses to drawer

---

## Key UX Principles

**1. Never block on auth**
The research flow works without signing in. Auth is for saving. This maximizes demo accessibility and reduces friction for portfolio viewers.

**2. The stream is the product, not a loader**
Don't treat the ReAct stream as a loading screen. It's a feature. Give it space. Make each step readable. This is what differentiates the demo.

**3. Partial data is better than failure**
If 5 of 8 fields are populated, show them. Don't hide behind a spinner waiting for 100% completeness. Render progressively.

**4. Talking points are the output, not the dossier**
The talking points section is why someone uses this tool before a call. Design hierarchy should lead the eye there after the overview.

**5. Mobile: stream collapses, dossier is full-width**
On mobile the stream log is collapsible. The dossier renders full-width below. Talking points are above the fold after scroll.

---

## Animations

Minimal. One deliberate motion per interaction:

- **Stream log entries:** `fadeInUp` (150ms, ease-out) as each step arrives — feels like data materializing
- **Dossier section reveal:** `fadeIn` (200ms) as sections populate with data
- **Complete banner:** subtle pulse on the green "Research complete" — draws the eye once, doesn't loop
- **Nothing else animated** — resist the urge to animate cards on scroll. It'll make it look like a template.

---

## Component Checklist

| Component | Notes |
|-----------|-------|
| `<SearchInput>` | Large, auto-focused, enter to submit |
| `<StreamLog>` | SSE event list, monospace, color-coded |
| `<ProgressBar>` | Tool call count x/12 |
| `<DossierReport>` | Full structured render, reused across pages |
| `<TalkingPointCard>` | Amber accent, distinct card style |
| `<KeyPersonCard>` | Name + role, small pill |
| `<NewsItem>` | Title + source + date + summary |
| `<DossierListItem>` | History row with hover preview |
| `<PartialDataBadge>` | "X/8 fields · partial" warning |
| `<AuthBanner>` | "Sign in to save" — dismissable, non-blocking |
| `<DeleteConfirmModal>` | Simple confirm/cancel |
| `<Navbar>` | Sticky, responsive |
| `<EmptyState>` | Reusable: icon + message + CTA |

---

## What NOT to Do

- No gradient hero backgrounds — this is a data tool, not a landing page
- No card hover animations with shadows that scale up — feels like a Tailwind template
- No numbered steps (01 / 02 / 03) as decorative section markers
- No dark-mode toggle — dark is the only mode, it fits the product
- No emoji in UI copy (stream log can use minimal icon glyphs but not emoji)
- No "Powered by Claude AI ✨" badge — let the quality speak
