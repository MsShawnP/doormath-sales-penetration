---
date: 2026-06-15
topic: door-math-distribution-penetration
---

# Door Math — Distribution Penetration Tracker

**Repo:** `door-math`
**Series:** CPG Sales Penetration Tools (Tool 1 of 5)
**Purpose:** Portfolio piece for lailarallc.com — must impress prospects engaging with the portfolio

## Business question

> "Of the stores that *could* carry this item, how many actually do — and is that number growing or quietly eroding?"

Distribution penetration is the denominator for everything downstream. Before anyone talks about velocity, household buyers, or repeat rates, the item has to exist in a store. Most brands can't state their distribution penetration accurately by retailer. This tool makes it visible.

## Core metrics

- **% of addressable doors carrying** — authorized doors ÷ total addressable doors, by item
- **Unweighted distribution** — raw % of stores carrying
- **Weighted distribution (ACV%)** — % of all-commodity volume flowing through carrying stores
- **TDP (Total Distribution Points)** — sum of ACV% across items; captures breadth (doors) and depth (items per door)
- **Authorized vs scanning gap** — the delta between "retailer says yes" and "the shelf says yes"

## Decided constraints

### Stack
CC decides. The goal is a polished portfolio piece that impresses prospects. Choose whatever stack is best suited to that outcome. If the repo has an existing scaffold that doesn't serve the goal, replace it. If it does, use it.

### Data model
`CINDERHAVEN_CANONICAL.md` governs. The brief's earlier reference to "3 banners / ~600 doors" is superseded — use the canonical 6 retailers / 640 doors. All item data comes from the canonical item set. Run `check_canonical.py` against any generated data.

### Store universe — shared package
Build the store universe as a separate versioned package (`cinderhaven-store-universe` or similar) that this tool and tools 2–5 import. Follow the same pinned-snapshot pattern as `check_canonical.py`: each downstream tool locks to a version of the store universe and bumps explicitly. A canonical change is a conscious propagation, not an accidental cascade.

The store universe package contains:
- Store/door list with banner, region, store volume tier (across canonical 6 retailers / 640 doors)
- Authorization matrix (item × door) with deliberate gaps
- Synthetic POS scan data (item × store × week) — scan flags sufficient
- A slow-leak story baked into the data: at least one SKU losing doors quarter over quarter without obvious signal. Define the SKU(s), quarter range, magnitude, and curve shape explicitly in the data fixture so the chart layer doesn't have to guess.

### Narrative approach — woven into the dashboard
No separate scrollytelling landing or narrative section. The story is told *through* the dashboard via contextual callouts, annotations, and guided highlights within the data views themselves. Users who read the numbers get the numbers. Users who need the "why this matters" context get it inline without being forced through a separate experience.

This means:
- No scroll-hijacking or forced pacing
- No separate narrative-to-dashboard transition to design
- Annotations and callouts must be visually distinct but not obstructive
- The slow-leak story should surface as an annotation or highlight that draws attention, not as a separate narrative beat

### Scorecard export
Both screen view and PDF/print. The one-page distribution scorecard must work as a printable PDF suitable for a buyer meeting. Specify content, information hierarchy, and paper size. Follow Lailara print rules from `LAILARA_DESIGN_SYSTEM.md`.

### MVP
All requirements are in scope. No phased cutline — the full tool is the deliverable.

## Implementation decisions

These were surfaced during plan review and are now resolved.

### Dependencies
- **Drop dash-bootstrap-components.** `lailara-frame.css` is the design system. Bootstrap CSS will compete with it. Replace any dbc layout components with plain Dash HTML.
- **Rename app.py → wsgi.py** to avoid Python import collision with the `app/` package.
- **Merge palette.py into constants.py.** Single consumer, no reason for the extra file.
- **Use "retailer" not "banner"** consistently throughout the codebase.

### Infrastructure
- **Fly.io VM: 1024MB.** WeasyPrint's pango/cairo stack will OOM at 512MB with 2 gunicorn workers. Bump the memory.
- **Fly.io auto_stop_machines: "stop" not "suspend."** Low-traffic portfolio piece. "Stop" is free when idle with 3–5s cold start. "Suspend" bills for idle memory with no benefit here.
- **Max-width: 1200px** from lailara-frame (removes any 900px override from the scaffold).

### Exception list (AG Grid)
- **Row selection expands a detail card** with item/store-level context for that exception.
- **Click-to-pin dismisses on filter change.**

### Trend view
- **Snap-to-nearest with tooltip** for click targets. Do not create 96 discrete per-point click targets on overlapping lines — that's unusable.

### Scorecard
- **Live filter update.** The scorecard updates in real time as filters change. No "Apply" gate. User sees their filtered scorecard and prints when it looks right.

### Mobile annotations
- **Small inline icon** (info or lightbulb style). Tap to expand inline (not overlay). Tap again or scroll past to dismiss.

### SKU dropdown
- **Retain selection if still valid** after a filter change. Reset to "all" if the selected SKU leaves the filtered set.

### Void Finder output contract
- **Ship CSV only.** Mark any JSON schema as "draft" — tool 5 doesn't exist yet, so there's no consumer to validate the contract.

### Testing
- **Manual checklists for mobile and accessibility testing.** Do not commit to Playwright or dash.testing for a solo portfolio piece. Write honest, runnable checklists.

### Auto-applied fixes from plan review
These are already incorporated in the plan but noted here for traceability: loading + error states in all views, U6→U4 dependency in sequencing, U5 dependencies updated to include components.py, `lailara_frame.py` in file list and output structure, portfolio card exclusion from this repo's scope.

## Outputs

1. **Dashboard with four views:**
   - Door-count view by item, banner, region
   - ACV% and TDP trend lines (is distribution building or bleeding?)
   - Authorized-but-not-scanning exception list
   - One-page distribution scorecard (screen + PDF/print)

2. **Shared store universe package** (versioned, importable by tools 2–5)

3. **Portfolio card** on lailarallc.com `/work` page

## Spec gaps CC must resolve

These were identified in the planning review. CC should make these calls during implementation, not defer them:

- **Dashboard navigation model:** How do the four views connect? Tabs, sidebar, routes? Does filter state persist across view switches?
- **Filter mechanics:** Control types (dropdown, multi-select, range), placement, empty-state behavior, time-period control format.
- **Empty, loading, and error states:** All four views need them. Filter-to-zero-rows is guaranteed with 50 SKUs × banners × time.
- **Hero metric:** Which metric leads, what framing copy makes it legible to a non-CPG audience, static vs. animated.
- **Auth gap visualization:** Chart type, animation, explanatory annotations for the inline narrative.
- **Exception list table:** Columns, default sort, grouping model, pagination strategy for 50 SKUs × banners. (Row selection behavior and dismiss-on-filter are decided above.)
- **Mobile:** Desktop primary, but define what happens on mobile viewports. Annotation collapse behavior is decided above; remaining mobile layout decisions are CC's call.
- **Accessibility:** Set a WCAG target. Keyboard navigation for any interactive charts. Keyboard alternatives for any animated elements.

## References

- `CINDERHAVEN_CANONICAL.md` — item set, retailer list, locked figures
- `check_canonical.py` — canonical data guard
- `LAILARA_DESIGN_SYSTEM.md` — visual design system, print rules, typography
- Portfolio deployment target: Fly.io (1024MB VM, auto_stop_machines: "stop", consistent with existing portfolio apps)
- Existing portfolio pattern: `/work` page card linking to deployed app

## Sequencing note

This is tool 1 of 5 in the CPG sales penetration series. The store universe and authorization matrix built here are the foundation for the remaining four tools. The shared package must be right — everything downstream inherits from it.
