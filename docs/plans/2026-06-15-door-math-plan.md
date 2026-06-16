---
type: feat
origin: docs/brainstorms/2026-06-15-door-math-requirements.md
plan_depth: standard
status: active
created: 2026-06-15
---

# Door Math — Distribution Penetration Tracker

## Problem Frame

Distribution penetration is the denominator for everything downstream in CPG sales. Before anyone talks about velocity, household buyers, or repeat rates, the item has to exist in a store. Most brands cannot state their distribution penetration accurately by retailer.

This tool answers: "Of the stores that could carry this item, how many actually do — and is that number growing or quietly eroding?"

**Scope:** Full four-view dashboard + shared store-universe package + PDF scorecard. No phased cutline — the full tool is the deliverable (see origin: `docs/brainstorms/2026-06-15-door-math-requirements.md`).

**Out of scope:** Tools 2-5 in the CPG series (Velocity, Household Panel, Trade Spend, Void Finder). Portfolio card on lailarallc.com `/work` page (deferred to deployment time).

## Key Technical Decisions

### KTD-1: Stack — Keep Python/Dash

**Decision:** Retain the existing Python 3.11 / Dash 3.x / Plotly / AG Grid scaffold.

**Rationale:** The requirements doc delegates this to CC. Research across ~30 published portfolio tools shows Dash is the data-dense tool pattern — the 4 most complex Cinderhaven analytics tools use Dash. Switching to React would require rebuilding the chart layer, creating a Python API backend for data, and losing pandas integration. Specific Dash advantages for this tool:
- AG Grid is best-in-class for the exceptions table (filtering, sorting, pagination, export)
- Plotly produces SVG charts out of the box (Economist-style print requirement)
- The shared store-universe package is Python — same-language consumer avoids cross-language complexity
- `lailara-frame` integration is already built for Dash
- WeasyPrint for PDF generation is proven in the portfolio (production-demand-forecast uses it)

**Alternatives considered:** React/Vite + Observable Plot (used by where-the-money-comes-from). Better for custom animations and lightweight chart setups, but net negative for a data-dense tool where AG Grid tables, Plotly SVG, and Python data manipulation are the core value.

### KTD-2: Navigation — Horizontal Tabs with Persistent Filters

**Decision:** Four horizontal tabs below the brand frame header. Filter state persists across tab switches via `dcc.Store` (session storage).

**Rationale:** Four views is the natural fit for a tab bar — sidebar navigation makes sense for 10+ modes (like retail-velocity-decision-tool) but adds unnecessary chrome for four peer-level views. Persistent filter state prevents the frustration of re-selecting filters when switching views to compare different facets of the same retailer/product line.

**Tab order:** Door Count → Trends → Exceptions → Scorecard. This follows the analytical narrative: see the current state, see the trajectory, see the problems, get the summary.

### KTD-3: Filter Architecture

**Decision:** Shared horizontal filter bar between tabs and content area. All views share the same filter context.

| Control | Type | Behavior |
|---------|------|----------|
| Retailer | Multi-select dropdown | All selected by default. Options: 6 canonical retailers. |
| Product Line | Multi-select dropdown | All selected by default. Options: 5 canonical product lines. |
| SKU | Searchable dropdown | Appears when exactly one product line is selected. Optional — filters to specific item. Retains selection if still valid after filter change; resets to "all" if the selected SKU leaves the filtered set. |
| Time Period | Quarter range selector | Two dropdowns: start quarter and end quarter. Default: most recent 4 quarters. |

**Empty state:** Centered message — "No data matches the current filters" with a "Reset filters" button that restores all defaults. Every view handles this identically.

**Filter persistence:** `dcc.Store(id='filter-state', storage_type='session')` holds a JSON dict of current selections. Each tab's callbacks read from this store. The filter bar component writes to it on any change. `filters.py` initializes the store with all-defaults on first visit (before any view callback fires) so views never receive `None` from the store.

**Loading state:** `dcc.Loading` wraps each view's content area (not individual charts). Overlay spinner in navy (`#1f2e7a`) on semi-transparent canvas background. Stale data is replaced by the spinner during refresh — no stale-data-visible period. Defined once in `layout.py`, applied consistently to all 4 views.

**Error state:** Inline error component using Lailara Fail semantic color (red surface `#fde8e7`, text `#7a0906`). Displays: "Something went wrong. [Retry]" with a button that re-triggers the callback. For PDF generation failures (U6), the "Download PDF" button shows "PDF generation failed — try again" in the same error style. Defined in `components.py` as `error_banner(message, retry_callback_id)`.

### KTD-4: Hero Metric

**Decision:** "% of addressable doors carrying at least one Cinderhaven item" leads the scorecard and appears as a headline number on the Door Count view.

**Framing copy:** `XX%` in Playfair Display 64px headline number, with subtext: "of addressable doors carry at least one Cinderhaven item" in Source Sans 3 17px. Below that, a one-line trend indicator: "↑ X.X pp from prior quarter" or "↓ X.X pp from prior quarter" with directional color (teal for up, Tokyo-40 for down).

**Rationale:** This is the single number a brand manager or buyer can evaluate without CPG context. "% of doors carrying" is intuitive; ACV% and TDP require explanation that belongs in the detail views. Animated count-up (250ms via requestAnimationFrame) per Lailara interaction patterns; snaps to final value under `prefers-reduced-motion`.

### KTD-5: Auth Gap Visualization

**Decision:** Paired horizontal bar chart — one bar per retailer showing authorized door count (navy, `#1f2e7a`) and scanning door count (teal, `#158f75`). Gap annotated with delta value between the bars.

**Interaction:** Click-to-pin on a retailer shows a dark callout card listing the specific SKUs in the gap for that retailer (SKU ID, item name, weeks since last scan). Non-selected retailers dim to 0.3 opacity.

**Narrative annotation:** A contextual callout appears when the gap exceeds a threshold (>15% of authorized doors not scanning). The callout uses the Lailara insight-line style (left border accent 3px, Source Sans 3 15px) and explains what the gap means: "X stores are authorized but haven't scanned in Y+ weeks — the shelf says no even though the retailer said yes."

### KTD-6: Exception List Table

**Decision:** AG Grid table with the following specification.

| Column | Width | Notes |
|--------|-------|-------|
| SKU ID | 120px | Format: CHP-XX-NNN |
| Item Name | 200px | Truncate with tooltip |
| Product Line | 140px | Full name |
| Retailer | 140px | |
| Store ID | 100px | |
| Region | 100px | |
| Authorized Date | 120px | Format: YYYY-Wnn |
| Last Scan Date | 120px | Format: YYYY-Wnn |
| Weeks Silent | 100px | Bold when > 8 weeks |
| Store Volume Tier | 80px | A/B/C |

**Default sort:** Weeks Silent descending (longest gaps first — highest-priority voids surface at top).

**Grouping:** Row grouping by retailer, collapsible. Expand/collapse all toggle.

**Pagination:** 25 rows per page via AG Grid pagination. Total row count displayed.

**Row selection:** Selecting a row expands a detail card below the row with item/store-level context for that exception (authorized date, last scan date, store address, volume tier, weeks silent, product line context). Single selection — clicking another row moves the detail card. Click-to-pin dismisses on filter change (per KTD-8).

**Export:** CSV download only (for spreadsheet users). Void Finder (tool 5) doesn't exist yet — no JSON contract until there's a consumer to validate it.

### KTD-7: Void Finder Output — CSV Only

**Decision:** Ship CSV export only from the exceptions view. No JSON contract until Void Finder (tool 5) exists and can validate the schema.

**Rationale:** Locking a versioned JSON contract before the consumer exists invites silent drift. CSV is immediately useful for spreadsheet workflows. When tool 5 is planned, define the JSON schema then — with a real consumer to validate against.

### KTD-8: Interaction Model — Click-to-Pin

**Decision:** Click-to-pin per Lailara design system. Single selection per chart (click another element to switch; click the same element to dismiss).

**Per-view detail card content:**
- **Door Count:** Retailer name, door count / addressable doors, penetration %, items carried, items not carried
- **Trends:** Quarter label, ACV% value, TDP value, period-over-period delta, items gained/lost. Click targets use snap-to-nearest with tooltip — not 96 discrete per-point targets on overlapping lines.
- **Exceptions:** AG Grid row selection expands a detail card below the selected row (item/store-level context). No dark callout card — the detail is inline.
- **Scorecard:** Live filter update — scorecard content updates in real time as filters change. No "Apply" gate. User filters, sees the result, prints when it looks right.

**Filter-change behavior:** Any filter change dismisses the active callout card and resets pin state to none. This prevents stale card data from remaining visible after the underlying chart data changes.

**Dark callout card:** Positioned above the chart. London-10 background (`#1a1a1a`), white primary text, `#d8d8d8` subtitle, `rgba(255,255,255,0.12)` internal dividers. 200ms ease-out fade transition.

### KTD-9: Mobile Strategy

**Decision:** Desktop primary. Graceful degradation at <640px mobile breakpoint.

| Element | Mobile behavior |
|---------|----------------|
| Tabs | Horizontal scroll with active indicator (no vertical stack — keeps spatial model) |
| Filter bar | Collapses to a "Filters" toggle button that expands a full-width panel |
| Charts | Horizontal scroll within container; minimum chart width 600px |
| AG Grid | Horizontal scroll with frozen first column (SKU ID) |
| Annotations | Collapse to small inline icon (ⓘ info/lightbulb style). Tap to expand inline (not overlay). Tap again or scroll past to dismiss. |
| Scorecard PDF button | Hidden (print not useful on mobile) |
| Hero metric | Font scale per design system (64px → 44px) |

### KTD-10: Accessibility — WCAG AA

**Decision:** Target WCAG 2.1 AA.

- All charts have `aria-label` describing the data summary
- Tab navigation via arrow keys (Dash built-in for `dcc.Tabs`)
- Focus-visible: 2px solid text-primary, 2px offset (per Lailara design system)
- `prefers-reduced-motion`: number animations snap to final value, opacity transitions instant
- Color is never the sole channel — every data point has a text label (Economist chart rule)
- AG Grid keyboard navigation (built-in)
- Skip-to-content link for screen readers

### KTD-11: Slow-Leak Story Definition

**Decision:** Two SKUs with deliberate door erosion baked into the data fixture.

**Primary leak — CHP-DG-003 (Dried Goods):**
- Quarter range: Q2 2024 → Q4 2025 (7 quarters)
- Starting penetration: 85% of addressable doors (across all retailers)
- Ending penetration: 52%
- Curve: Gradual start (2-3 doors lost/quarter in Q2-Q3 2024), accelerating (5-8 doors/quarter in 2025)
- Retailers affected: Regional Group first → Sprouts → Kroger. Walmart and Costco stable.
- No obvious signal — the item isn't discontinued, authorized everywhere, just quietly disappearing from shelves

**Secondary leak — CHP-SC-007 (Specialty Condiments):**
- Quarter range: Q3 2024 → Q4 2025 (6 quarters)
- Starting penetration: 72%
- Ending penetration: 58%
- Curve: Steady, approximately linear decline
- Retailers affected: Distributed across all retailers proportionally

The primary leak is dramatic enough to surface in trend charts. The secondary is subtle — it tests whether the dashboard makes slow erosion visible even when the magnitude is modest.

### KTD-12: Store Universe Package Architecture

**Decision:** `packages/cinderhaven-store-universe/` as a subdirectory within the Door Math repo, structured as an installable Python package.

**Rationale:** Tools 2-5 don't exist yet. A monorepo subdirectory keeps everything in one Docker build context (simplifies Fly.io deployment) while still being a proper versioned package. When tools 2-5 are built, they can install from a path dependency initially and the package can be extracted to its own repo if needed.

**Package structure:**
```
packages/cinderhaven-store-universe/
├── pyproject.toml              # version: 0.1.0
├── README.md
├── src/
│   └── cinderhaven_store_universe/
│       ├── __init__.py         # public API: get_stores(), get_auth_matrix(), get_scan_data(), get_slow_leak_config()
│       ├── stores.py           # 640 doors across 6 retailers with region, volume tier
│       ├── authorization.py    # item x door authorization matrix with deliberate gaps
│       ├── scans.py            # synthetic POS scan data (item x store x week)
│       ├── slow_leak.py        # slow-leak story configuration and data generation
│       └── constants.py        # retailer IDs, SKU IDs, product line codes from canonical
└── tests/
    ├── test_canonical.py       # validates against CINDERHAVEN_CANONICAL.md constraints
    └── test_slow_leak.py       # verifies leak curve matches specification
```

**Version pinning:** Door Math's `pyproject.toml` declares a path dependency: `cinderhaven-store-universe = {path = "packages/cinderhaven-store-universe", develop = true}`. The package version in its own `pyproject.toml` is bumped explicitly on data changes.

### KTD-13: PDF Scorecard Specification

**Decision:** WeasyPrint generates a one-page PDF from a dedicated HTML template.

**Content and hierarchy (letter size, portrait, 0.6in margins):**
1. **Header:** Cinderhaven Provisions logo area + "Distribution Scorecard" + quarter label + generation date
2. **Hero block:** % addressable doors carrying (64pt Playfair Display) + trend arrow + subtext
3. **Retailer summary table:** 6 rows, columns: Retailer, Doors Carrying / Addressable, Penetration %, ACV%, TDP, Δ vs Prior Quarter
4. **Product line summary:** 5 rows, same column structure
5. **Top exceptions:** 10 highest weeks-silent items from the exception list
6. **Footer:** Running footer per Lailara print rules — brand text bottom-left, page counter bottom-right, 9pt Source Sans 3, `#595959`

**Print rules:** White background, no interactive controls, SVG charts render as vectors, `@page` letter size with 0.6in margins. All per `LAILARA_DESIGN_SYSTEM.md`.

**WeasyPrint deployment:** Pin to `>=68.0,<69.0` (CVE in earlier versions). Dockerfile apt packages for Debian Trixie: `libpango-1.0-0`, `libpangoft2-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-xlib-2.0-0`, `libffi-dev`, `fonts-liberation`. (see learnings: `weasyprint-dockerfile-debian-trixie-deps-2026-05-31.md`)

### KTD-14: Time Anchor for Synthetic Data

**Decision:** Define a `DEMO_AS_OF_DATE` constant set to `2025-12-29` (end of Q4 2025, the last complete week in the synthetic data). Thread it through every time-relative computation — trend calculations, "weeks since last scan," period defaults.

**Rationale:** The synthetic data covers 2024-2025. Wall-clock time is 2026. Any function that uses `pd.Timestamp.today()` or `datetime.now()` will produce silently wrong output. This bug class is invisible — no errors, just wrong numbers. (see learnings: `kpi-as-of-date-demo-data-past-due-2026-05-31.md`)

## Implementation Units

### U1: Store Universe Package

**Goal:** Build the shared data foundation as a versioned Python package with canonical validation.

**Files:**
- `packages/cinderhaven-store-universe/pyproject.toml` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/__init__.py` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/constants.py` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/stores.py` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/authorization.py` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/scans.py` — create
- `packages/cinderhaven-store-universe/src/cinderhaven_store_universe/slow_leak.py` — create
- `packages/cinderhaven-store-universe/tests/test_canonical.py` — create
- `packages/cinderhaven-store-universe/tests/test_slow_leak.py` — create
- `packages/cinderhaven-store-universe/README.md` — create

**Approach:**
- `constants.py` defines all canonical IDs: 50 SKU IDs (CHP-{XX}-NNN), 6 retailer IDs (RET-*), 5 product line codes, door counts per retailer. Source of truth: `CINDERHAVEN_CANONICAL.md`.
- `stores.py` generates 640 store records with store_id, retailer_id, region (4 US regions), and volume tier (A/B/C distributed realistically — Walmart skews A, Regional Group skews C).
- `authorization.py` generates the item x door authorization matrix. Not every item is authorized at every door — deliberate gaps create the foundation for the exception list. Authorization rate varies by retailer and product line (Whole Foods authorizes all specialty items; Walmart authorizes only top sellers).
- `scans.py` generates weekly POS scan flags (item x store x week) for the Q1 2024 → Q4 2025 range. A scan flag of `True` means the item rang at that store that week. Incorporates the slow-leak pattern.
- `slow_leak.py` defines the two leak configurations (CHP-DG-003 and CHP-SC-007 per KTD-11) and provides a `apply_slow_leak(scan_data)` function that modifies scan flags to create the erosion pattern.
- `DEMO_AS_OF_DATE = pd.Timestamp('2025-12-29')` lives in constants and is exported.
- `test_canonical.py` validates: exactly 50 SKUs, exactly 640 doors, correct door counts per retailer, correct retailer IDs, SKU format matches CHP-{XX}-NNN. Exit-0/exit-1 gate pattern following `check_canonical.py`.
- `test_slow_leak.py` validates: CHP-DG-003 penetration decreases from ~85% to ~52% over the specified quarters; CHP-SC-007 decreases from ~72% to ~58%; curves match specified shapes within tolerance.

**Dependencies:** None — this is the foundation unit.

**Test scenarios:**
1. Store count per retailer matches canonical (Walmart 180, Costco 60, etc.)
2. Total store count is exactly 640
3. SKU count is exactly 50 across 5 product lines of 10
4. SKU IDs match CHP-{XX}-NNN format with correct product line codes
5. Authorization matrix has deliberate gaps (not 100% authorization rate)
6. Scan data covers Q1 2024 through Q4 2025 weekly
7. CHP-DG-003 slow leak: penetration drops 33pp over 7 quarters with accelerating curve
8. CHP-SC-007 slow leak: penetration drops 14pp over 6 quarters with linear curve
9. Non-leak SKUs maintain stable or growing penetration
10. `DEMO_AS_OF_DATE` is 2025-12-29

### U2: App Shell, Palette, and Brand Frame

**Goal:** Replace the scaffold shell with the Lailara brand frame, set up the tab navigation, shared filter bar, and design system integration.

**Files:**
- `app/constants.py` — create (Lailara palette as Python constants + semantic color aliases + format helpers + `DEMO_AS_OF_DATE` re-export)
- `app/app.py` — create (replaces root `app.py`)
- `app/layout.py` — create (brand frame + tabs + filter bar + content area)
- `app/filters.py` — create (shared filter bar component + dcc.Store callbacks)
- `app/__init__.py` — create
- `app/lailara_frame.py` — vendor from `lailara-frame` kit (brand frame wrap function, inside `app/` per velocity-tool pattern)
- `assets/lailara-frame.css` — vendor from `lailara-frame` kit
- `assets/fonts/playfair-display-latin.woff2` — vendor
- `assets/fonts/playfair-display-latin-ext.woff2` — vendor
- `assets/fonts/source-sans-3-latin.woff2` — vendor
- `assets/fonts/source-sans-3-latin-ext.woff2` — vendor
- `assets/style.css` — rewrite (remove Google Fonts CDN, keep only project-specific overrides)
- `wsgi.py` — create (thin entry point importing from `app/`; named `wsgi.py` to avoid Python import collision with the `app/` package)
- `tests/test_app_shell.py` — create

**Approach:**
- Vendor `lailara-frame.css` and 4 woff2 font files from `C:\Users\mssha\projects\active\lailara-frame\`. Vendor the `lailara_frame.py` wrap function or replicate its pattern (brand header linking lailarallc.com + standard footer).
- `constants.py` defines all Lailara hex values as Python constants (Plotly traces need Python-side values, not CSS vars), semantic aliases (`TREND_UP = HK_35`, `TREND_DOWN = TOKYO_40`, `AUTH_BAR = CHICAGO_20`, `SCAN_BAR = HK_35`), format helpers, and re-exports `DEMO_AS_OF_DATE` from store universe. Single file — no separate palette module. (see learnings: `centralized-brand-palette-module.md`)
- `layout.py` assembles: brand frame header → tab bar (4 tabs) → filter bar → content area (rendered by active tab). Uses `dcc.Tabs` with `dcc.Tab` children.
- `filters.py` builds the filter bar component (retailer multi-select, product line multi-select, conditional SKU dropdown, quarter range selectors) and registers callbacks that write to `dcc.Store('filter-state')`.
- `style.css` is stripped to project-specific overrides only. All design tokens come from `lailara-frame.css`. No hex values outside `:root`. Content max-width follows `lailara-frame.css` at 1200px (the existing scaffold's 900px override is removed). (see learnings: `css-design-token-drift-2026-05-28.md`)
- `wsgi.py` at root becomes a thin entry point: imports the Dash app from `app/app.py`, adds health check endpoint, runs gunicorn in dev mode. Named `wsgi.py` (not `app.py`) to avoid Python import collision — when both `app.py` and `app/` exist, Python resolves the package directory over the file, causing `gunicorn app:server` to fail.
- Delete old scaffold files: `pages/` directory (replaced by tab-based architecture), old `data/synthetic.py` (replaced by store universe package), old `app.py` (replaced by `wsgi.py`).

**Dependencies:** U1 (store universe package must be installable for filter option population).

**Test scenarios:**
1. App starts without error and serves on configured port
2. Health endpoint returns 200 with `{"status": "ok"}`
3. All 4 tabs render without error
4. Filter bar renders with correct options (6 retailers, 5 product lines)
5. Filter state persists across tab switches
6. Selecting one product line reveals SKU dropdown
7. Empty filter combination shows "No data matches" message with reset button
8. No Google Fonts CDN requests (self-hosted fonts only)
9. Brand frame header and footer render correctly
10. Hex grep audit: no raw hex values outside `:root` and `constants.py`

### U3: Door Count View

**Goal:** Build the primary view showing distribution penetration by item, retailer, and region.

**Files:**
- `app/views/door_count.py` — create
- `app/views/__init__.py` — create
- `app/charts.py` — create (shared chart utilities — Economist-style defaults, click-to-pin wiring)
- `app/components.py` — create (shared UI components — dark callout card, annotation callout)
- `tests/test_door_count.py` — create

**Approach:**
- Hero metric at top: % addressable doors carrying (per KTD-4). Playfair Display headline number with animated count-up. Trend indicator below.
- Main chart: Horizontal grouped bar chart — one group per retailer, bars for "authorized" (navy) and "carrying" (teal). Each bar labeled with count and percentage.
- Secondary chart: Stacked bar by product line showing penetration across retailers. Teal sequential palette (darkest = highest penetration).
- Click-to-pin: clicking a retailer bar shows dark callout card with retailer-specific detail (per KTD-8). Non-selected dims to 0.3. (see learnings: `interactive-analytics-deliverable-architecture-2026-05-26.md`)
- Narrative annotation: When the auth gap for any retailer exceeds 15%, an insight-line callout appears explaining the gap (per KTD-5). The callout text is computed from the data, not hardcoded.
- `charts.py` provides `economist_layout()` (applies Lailara chart defaults: canvas background, horizontal gridlines only, Source Sans 3 axis text, no decorative elements) and `click_to_pin_callback()` (shared click handler pattern).
- `components.py` provides `dark_callout_card(title, rows)` and `annotation_callout(text)` Dash components.
- All calculations use `DEMO_AS_OF_DATE` for the "current" quarter.

**Dependencies:** U1 (data), U2 (shell, palette, filters).

**Test scenarios:**
1. View renders with default filters (all retailers, all product lines, last 4 quarters)
2. Hero metric shows correct % addressable doors carrying
3. Retailer bar chart shows correct authorized vs carrying counts for each retailer
4. Product line chart shows correct penetration breakdown
5. Click on retailer bar pins detail card with correct data
6. Click same bar again dismisses card
7. Non-selected elements dim to 0.3 opacity
8. Annotation callout appears when auth gap > 15%
9. Annotation text is computed from data (not hardcoded)
10. Filtering by retailer/product line updates all charts correctly
11. Charts render as SVG (not canvas)

### U4: Trends View

**Goal:** Build ACV% and TDP trend lines showing whether distribution is building or bleeding.

**Files:**
- `app/views/trends.py` — create
- `app/calculations.py` — create (ACV%, TDP, penetration rate calculations)
- `tests/test_trends.py` — create
- `tests/test_calculations.py` — create

**Approach:**
- `calculations.py` centralizes all metric computations: `calc_penetration_rate()`, `calc_acv_pct()`, `calc_tdp()`, `calc_period_delta()`. Each accepts an explicit `as_of_date` parameter (defaults to `DEMO_AS_OF_DATE`). Store volume tiers feed ACV% weighting (tier A = high ACV, tier C = low ACV).
- Top section: Two side-by-side line charts — ACV% over time (left) and TDP over time (right). X-axis: quarters. Y-axis: percentage / points. Lines per retailer, colored from teal sequential palette.
- Slow-leak annotation: When CHP-DG-003's trend line drops below a threshold, an annotation callout appears highlighting the erosion. Same for CHP-SC-007 if visible at current filter level. Annotation text computed from the data: "CHP-DG-003 has lost X doors across Y quarters — penetration down from Z% to W%."
- Click-to-pin on a data point shows the dark callout card with quarter detail (per KTD-8).
- Period-over-period comparison: Each chart shows a dashed reference line for the benchmark (median across all retailers).

**Dependencies:** U1 (data), U2 (shell, palette, filters), U3 (shared chart/component utilities from `charts.py` and `components.py`).

**Test scenarios:**
1. ACV% line chart renders with correct quarterly values per retailer
2. TDP line chart renders with correct quarterly values
3. Slow-leak annotation surfaces for CHP-DG-003 at appropriate threshold
4. Click-to-pin on a data point shows quarter detail card
5. Benchmark reference line shows correct median
6. Filtering by retailer shows only selected retailer trend lines
7. Filtering by product line recalculates ACV%/TDP for that subset
8. Time period filter adjusts x-axis range
9. All calculations use `DEMO_AS_OF_DATE`, not wall-clock time
10. Trend direction (up/down arrow, teal/red color) is correct for each retailer

### U5: Exceptions View

**Goal:** Build the authorized-but-not-scanning exception list with AG Grid table and export capability.

**Files:**
- `app/views/exceptions.py` — create
- `app/export.py` — create (CSV export function)
- `tests/test_exceptions.py` — create
- `tests/test_export.py` — create

**Approach:**
- AG Grid table configured per KTD-6: 10 columns, default sort by weeks silent descending, row grouping by retailer, 25 rows per page.
- `export.py` provides `export_csv(exception_rows)`. CSV only — no JSON contract until Void Finder (tool 5) exists (per KTD-7).
- Export button: "Download CSV" above the table. Use `dcc.Download` for file delivery.
- Summary stats above the table: total exceptions count, average weeks silent, top 3 retailers by exception count.
- Weeks Silent column: bold text when > 8 weeks, Tokyo-40 color when > 12 weeks (visual urgency signal).
- Narrative annotation: If total exceptions exceed a threshold (>10% of authorized items not scanning), a callout appears summarizing the gap.

**Dependencies:** U1 (data), U2 (shell, palette, filters), U3 (shared `components.py` for `annotation_callout()`).

**Test scenarios:**
1. Exception table renders with correct columns and data
2. Default sort is weeks silent descending
3. Row grouping by retailer works (expand/collapse)
4. Pagination shows 25 rows per page
5. CSV export produces valid CSV with correct columns
6. Weeks Silent styling: bold > 8 weeks, Tokyo-40 > 12 weeks
7. Summary stats (count, avg weeks silent, top retailers) are correct
8. Filter changes update the exception list
9. Annotation appears when exceptions > 10% of authorized

### U6: Scorecard View and PDF Export

**Goal:** Build the one-page distribution scorecard for both screen display and PDF/print export.

**Files:**
- `app/views/scorecard.py` — create
- `app/pdf.py` — create (WeasyPrint HTML template → PDF generation)
- `app/templates/scorecard.html` — create (Jinja2 template for PDF)
- `tests/test_scorecard.py` — create
- `tests/test_pdf.py` — create

**Approach:**
- Screen view mirrors the PDF content (KTD-13): hero metric → retailer summary table → product line summary → top 10 exceptions. Updates live as filters change — no "Apply" gate.
- `scorecard.py` builds the Dash layout matching the PDF information hierarchy. Uses Dash HTML components (not Plotly charts) for the tables — pure HTML tables style better in print.
- `pdf.py` uses WeasyPrint to render `templates/scorecard.html` (a Jinja2 template) to PDF. Template receives the same data dict as the Dash view. All styling inline or in a `<style>` block — no external CSS dependencies.
- Color values in the PDF template come from `constants.py` via Jinja2 context, not hardcoded hex. (see learnings: `centralized-brand-palette-module.md`)
- "Download PDF" button triggers a server-side callback that generates the PDF and returns it via `dcc.Download`.
- Print rules per Lailara design system: `@page` letter portrait, 0.6in margins, running footer (brand bottom-left, page bottom-right, 9pt Source Sans 3, `#595959`), white background, no interactive controls.
- WeasyPrint pinned to `>=68.0,<69.0`. Cannot test on Windows — Docker-based smoke test required.

**Dependencies:** U1 (data), U2 (shell, palette), U4 (calculation functions from `calculations.py`).

**Test scenarios:**
1. Screen scorecard renders with correct hero metric
2. Retailer summary table shows 6 rows with correct data
3. Product line summary shows 5 rows with correct data
4. Top 10 exceptions list shows highest weeks-silent items
5. PDF download produces a valid PDF file
6. PDF is single page (letter portrait)
7. PDF uses correct Lailara fonts and colors (not system defaults)
8. PDF running footer shows brand text and page number
9. PDF tables have correct data matching screen view
10. Filter changes update scorecard data (but PDF always shows current filter state at time of generation)
11. Docker-based PDF smoke test passes: `python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf('/tmp/test.pdf')"`

### U7: Deployment, Mobile, and Polish

**Goal:** Update Dockerfile for WeasyPrint, finalize mobile responsive behavior, accessibility pass, README, and deploy to Fly.io. (Note: Portfolio card on lailarallc.com `/work` page is NOT part of this unit — deferred per scope statement.)

**Files:**
- `Dockerfile` — rewrite (add WeasyPrint system deps, copy store universe package)
- `fly.toml` — update (health check, auto_stop_machines = "stop")
- `pyproject.toml` — update (add weasyprint dependency, store universe path dependency)
- `requirements.txt` — update or replace with pyproject.toml-driven installs
- `.gitignore` — verify covers `.env`, `*.key`, credentials
- `README.md` — create (per Lailara README template)
- `README.md` section: Mobile Testing Checklist — manual checklist for viewport-dependent behavior
- `README.md` section: Accessibility Testing Checklist — manual checklist for WCAG AA spot checks

**Approach:**
- Dockerfile: add `apt-get install` for WeasyPrint deps (per KTD-13 package list). Multi-stage build: copy `packages/cinderhaven-store-universe/` first, install it, then copy app code. Final stage runs gunicorn.
- `fly.toml`: 1024MB VM memory (WeasyPrint needs headroom), HTTP health check (path `/health`, interval 30s, grace 60s), `auto_stop_machines = "stop"` (free when idle; 3-5s cold start acceptable for a portfolio piece).
- Mobile responsive pass per KTD-9: test at 375px and 1440px. Verify tab horizontal scroll, filter collapse, chart scroll, AG Grid scroll, annotation inline expand/dismiss. Manual checklist in README — no Playwright or dash.testing automation for a solo portfolio piece.
- Accessibility pass per KTD-10: add aria-labels to charts, verify keyboard navigation, test focus-visible, verify `prefers-reduced-motion` behavior. Manual checklist in README.
- README per Lailara template: what it does, how to run it, stack, Cinderhaven context, data contract, live URL.
- CSS hex grep audit: verify no raw hex values outside `:root` and `constants.py`.
- Run canonical validation: `pytest packages/cinderhaven-store-universe/tests/test_canonical.py`.

**Dependencies:** All prior units (U1-U6).

**Test scenarios:**
1. Docker build succeeds with no errors
2. Docker container starts and serves on port 8050
3. Health endpoint returns 200 inside Docker
4. PDF generation works inside Docker (WeasyPrint smoke test)
5. App renders correctly at 1440px viewport
6. App renders correctly at 375px viewport (mobile)
7. Tab keyboard navigation works (arrow keys)
8. Focus-visible outlines appear on interactive elements
9. Charts have aria-labels
10. `prefers-reduced-motion` disables animations
11. No Google Fonts CDN requests in production
12. README exists and follows Lailara template
13. `.gitignore` covers `.env` and credential files
14. Canonical validation tests pass

## Output Structure

```
doormath-sales-penetration/
├── app/
│   ├── __init__.py
│   ├── app.py                  # Dash app factory
│   ├── lailara_frame.py        # Vendored brand frame wrapper
│   ├── layout.py               # Brand frame + tabs + filter bar
│   ├── filters.py              # Shared filter components + callbacks
│   ├── constants.py            # Lailara palette + semantic aliases + format helpers + DEMO_AS_OF_DATE
│   ├── charts.py               # Economist-style chart defaults + click-to-pin
│   ├── components.py           # Dark callout card, annotation callout
│   ├── calculations.py         # ACV%, TDP, penetration rate functions
│   ├── export.py               # CSV export
│   ├── pdf.py                  # WeasyPrint PDF generation
│   ├── templates/
│   │   └── scorecard.html      # Jinja2 template for PDF scorecard
│   └── views/
│       ├── __init__.py
│       ├── door_count.py
│       ├── trends.py
│       ├── exceptions.py
│       └── scorecard.py
├── assets/
│   ├── lailara-frame.css       # Vendored design system
│   ├── style.css               # Project-specific overrides only
│   └── fonts/
│       ├── playfair-display-latin.woff2
│       ├── playfair-display-latin-ext.woff2
│       ├── source-sans-3-latin.woff2
│       └── source-sans-3-latin-ext.woff2
├── packages/
│   └── cinderhaven-store-universe/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       │   └── cinderhaven_store_universe/
│       │       ├── __init__.py
│       │       ├── constants.py
│       │       ├── stores.py
│       │       ├── authorization.py
│       │       ├── scans.py
│       │       └── slow_leak.py
│       └── tests/
│           ├── test_canonical.py
│           └── test_slow_leak.py
├── tests/
│   ├── test_app_shell.py
│   ├── test_door_count.py
│   ├── test_trends.py
│   ├── test_exceptions.py
│   ├── test_export.py
│   ├── test_scorecard.py
│   ├── test_pdf.py
│   └── test_calculations.py
├── wsgi.py                     # Thin entry point (not app.py — avoids import collision with app/)
├── Dockerfile
├── fly.toml
├── pyproject.toml
├── .gitignore
└── README.md
```

**Files to delete:** `pages/` directory (4 old stubs), `data/synthetic.py`, `data/__init__.py`, old root `app.py` (replaced by `wsgi.py`), `requirements.txt` (replaced by pyproject.toml), `tests/test_placeholder.py`.

## Risks & Dependencies

### R1: WeasyPrint Cannot Be Tested on Windows (HIGH)

WeasyPrint requires system libraries (pango, cairo) that are not available on Windows. PDF generation can only be tested inside the Docker container or on a Linux machine.

**Mitigation:** Build a Docker-based smoke test early in U6. Run `docker build` and `docker run` with a PDF generation test before writing the full scorecard template. Do not leave PDF testing to the end.

### R2: CSS Token Drift (MEDIUM)

Hex values outside `:root` or `constants.py` will silently diverge from the design system. This is especially dangerous for the PDF scorecard where print fidelity matters.

**Mitigation:** Run hex grep audit (`#[0-9a-fA-F]{3,8}` across `*.css` and `*.py`) before milestone commits. Every hex match outside `:root` and `constants.py` is a violation. (see learnings: `css-design-token-drift-2026-05-28.md`)

### R3: Hardcoded Numbers in Narrative Annotations (MEDIUM)

If annotation text embeds specific numbers ("640 doors authorized"), those claims break silently when data parameters change.

**Mitigation:** All annotation text is computed from the data at render time. No hardcoded figures in annotation strings. The test suite verifies annotations are dynamic by checking that filter changes produce different annotation text.

### R4: Store Universe Package Versioning Complexity (LOW)

The monorepo subdirectory approach simplifies Docker builds but may create friction when tools 2-5 need independent version pins.

**Mitigation:** Acceptable for now. The package has a version in `pyproject.toml` and the monorepo structure is explicitly documented as extractable. When tool 2 is planned, evaluate whether to extract to a separate repo.

### D1: External Dependency — CINDERHAVEN_CANONICAL.md

All data generation validates against the canonical facts file. If canonical figures change, the store universe package must be regenerated and its version bumped.

### D2: External Dependency — lailara-frame

Brand frame CSS, fonts, and wrap pattern are vendored from `C:\Users\mssha\projects\active\lailara-frame\`. Changes to the frame kit require re-vendoring.

## Sequencing

```
U1 (Store Universe)  ──────────────────┐
                                        ├──→ U3 (Door Count)
U2 (App Shell + Palette) ──────────────┤
                                        ├──→ U4 (Trends) ──→ U6 (Scorecard + PDF)
                                        │
                                        ├──→ U5 (Exceptions)
                                        │
                                        └──→ U7 (Deploy + Polish) ← requires U3-U6
```

U1 and U2 can be built in parallel. U3-U5 can be built in any order after U1+U2. U6 depends on `calculations.py` from U4. U7 is the final integration pass.

**Recommended build order:** U1 → U2 → U3 → U4 → U5 → U6 → U7. This follows the analytical narrative and builds complexity incrementally — each view adds one new concept (bars → trends → tables → PDF).
