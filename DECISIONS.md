# Door Math — Decisions

## 2026-06-15 — Brainstorm phase

**Stack: Keep Python/Dash, don't switch to React.**
The requirements doc delegates stack choice to CC. Research across ~30 portfolio tools shows Dash is the data-dense tool pattern. AG Grid is best-in-class for the exceptions table, Plotly produces SVG charts for print, and the store universe package is Python. Switching to React would require rebuilding the chart layer and losing pandas integration for no net gain.

**Hybrid entry point: hero metric + four tabs.**
Some prospects want to explore all four views; others only want the summary. A hero metric above the tabs gives the quick-hit audience their answer while tabs provide depth for the explorers. No scrollytelling — narrative woven into the dashboard via annotations and callouts.

**Store universe as monorepo subdirectory, not separate repo.**
Tools 2-5 don't exist yet. A subdirectory at `packages/cinderhaven-store-universe/` keeps everything in one Docker build context while still being a proper versioned package. Extract to standalone repo when tool 2 is planned.

**Two slow-leak SKUs, not one.**
CHP-DG-003 (dramatic: 85%→52% over 7 quarters, accelerating) tests whether the dashboard surfaces obvious erosion. CHP-SC-007 (subtle: 72%→58% over 6 quarters, linear) tests whether it makes slow erosion visible when magnitude is modest.

**DEMO_AS_OF_DATE = 2025-12-29.**
Synthetic data covers 2024-2025. Wall-clock is 2026. Any function using `datetime.now()` produces silently wrong output. Pin all time-relative computations to this constant.

## 2026-06-15 — Plan review phase

**Drop dash-bootstrap-components.**
lailara-frame.css is the design system. Bootstrap CSS would compete with it. Replace any dbc layout components with plain Dash HTML.

**Merge palette.py into constants.py.**
Single consumer (this tool only). No reason for the extra file. Semantic aliases and format helpers live alongside the hex constants.

**Fly.io: 1024MB VM, auto_stop_machines="stop".**
512MB risks OOM with WeasyPrint's pango/cairo stack + 2 gunicorn workers. "Stop" is free when idle with 3-5s cold start; "suspend" bills for idle memory with no benefit for a low-traffic portfolio piece.

**CSV export only, no Void Finder JSON contract.**
Tool 5 doesn't exist yet. Locking a versioned JSON contract before the consumer exists invites silent drift. Ship CSV for spreadsheet users now; define JSON schema when tool 5 is planned.

**AG Grid row selection expands inline detail card.**
Not highlight-only, not disabled. Selecting a row shows item/store-level context below the row. Single selection model.

**Snap-to-nearest for trend view click targets.**
96 discrete per-point targets on overlapping lines is unusable. Snap-to-nearest with tooltip instead.

**Live scorecard filter update, no Apply gate.**
Scorecard updates in real time as filters change. User filters, sees the result, prints when it looks right.

**Manual test checklists for mobile and accessibility.**
No Playwright or dash.testing automation for a solo portfolio piece. Honest, runnable checklists in the README.

**SKU dropdown: retain if valid, reset if not.**
When filters change, keep the selected SKU if it's still in the filtered set. Reset to "all" if it leaves.

**Mobile annotations: inline icon, tap to expand inline.**
Not overlay. Small info/lightbulb icon. Tap to expand inline, tap again or scroll past to dismiss.

**wsgi.py entry point, not app.py.**
Having both `app.py` at root and `app/` as a package causes Python to resolve the package over the file. `gunicorn app:server` crashes in production. Institutional learning from velocity-tool's FAILURES.md.

## 2026-06-15 — Performance refactor

**Centralized data module (app/data.py) with pre-aggregation.**
Each view module was loading its own copy of ~2M scan rows and processing them per callback. Centralized into one module that loads once and pre-aggregates to ~150K quarterly carrying records. All views import from app.data.

**Parquet disk cache for pre-aggregated data.**
Raw scan aggregation takes 15s. Caching SCAN_QUARTERLY and LAST_SCAN as parquet files in `.cache/` drops warm startup to 1.3s. Cache key is a hash of (AUTH length, STORES length, DEMO_AS_OF_DATE) — changes when the store universe package changes.

**Data change protocol for synthetic data modifications.**
Before modifying any data generation logic (generator scripts, seed data, schema, constants in the store universe package): (1) list every file that will be touched, (2) describe what is changing and why — which authorization gaps, slow-leak curve numerics, affected SKUs/retailers, (3) explicitly confirm NOT modifying `CINDERHAVEN_CANONICAL.md` or any locked canonical figures, (4) wait for user approval before running the generator. This protocol exists because the store universe feeds all 5 Cinderhaven tools and canonical figures are authoritative — an accidental change propagates silently across tools.

**Disable Werkzeug reloader for local dev.**
`debug=True` with reloader enabled loads the data module twice (30s+ startup). Disabled reloader for `python wsgi.py` local runs. Production uses gunicorn which doesn't have this issue.

## 2026-06-16 — Rounds 3+4 visual polish

**Batch ACV%/TDP computation for Trends.**
The per-retailer-per-quarter loop (6 retailers × 8 quarters × 2 metrics = 96 calls) was slow. New `batch_acv_by_retailer()` and `batch_tdp_by_retailer()` in calculations.py filter auth once, join scan_quarterly once, and groupby `(retailer_id, quarter)` in a single pass. Verified parity with individual calls.

**Debug toolbar off by default, env-var opt-in.**
`wsgi.py` now uses `DASH_DEBUG=1` to enable. Previously hardcoded `debug=True` which showed the Dash devtools toolbar in screenshots and production.

**Scorecard Top Exceptions aggregated by SKU.**
Raw exception rows showed the same SKU repeated per-store (e.g. CHP-AS-001 × 10). Now grouped by `sku_id` with columns: Item Name, Retailers (comma-joined), Stores (nunique), Max Weeks Silent. Sorted by max weeks descending.

**Annotation accent bar uses GRIDLINE, not CARD_BG.**
The `annotation_callout()` component inline-styled the left border with `CARD_BG` (#1a1a1a, dark card background) instead of `GRIDLINE` (#d9d9d9, London-85). Corrected to match the design system's insight-line specification.
