# Door Math — Handoff

## Current phase

Performance refactor complete. All callbacks execute in <0.5s. All 4 tabs render with correct data. Three visual polish bugs remain before redeploy.

## What was done (2026-06-15)

### Session 1 — Scaffold
- Initialized git repo, created project scaffold
- Registered with Chat-Code bridge

### Session 2 — Brainstorm + Plan + Review
- Ran `/ce:brainstorm` — produced requirements doc at `docs/brainstorms/2026-06-15-door-math-requirements.md`
- Ran `/ce:plan` — produced implementation plan at `docs/plans/2026-06-15-door-math-plan.md`
  - Research agents analyzed repo patterns, stack, and institutional learnings
  - 14 Key Technical Decisions, 7 Implementation Units
- Ran headless `/ce:doc-review` on the plan (5 personas, 26 findings)
  - 9 findings auto-applied (including P0 app.py→wsgi.py import collision fix)
  - 11 remaining findings presented to user
- User rewrote requirements doc to incorporate all remaining findings as decided constraints
- Updated plan to match all user decisions (11 changes)

### Session 3 — Implementation (`/ce:work`)
- Executed all 7 units in order: U1 → U2 → U3 → U4 → U5 → U6 → U7
- U1: Store universe package — 640 doors, 6 retailers, 50 SKUs, authorization matrix, POS scans, slow-leak stories
- U2: App shell — constants.py palette, lailara-frame.css, tab navigation, filter bar, wsgi.py entry point
- U3: Door count view — hero metric, retailer bar chart, product line stacked bar, click-to-pin cards, auth gap annotations
- U4: Trends view — ACV% and TDP line charts, slow-leak annotations, snap-to-nearest interaction
- U5: Exceptions view — AG Grid table, row selection detail, CSV export, summary stats
- U6: Scorecard view — screen scorecard with live filters, WeasyPrint PDF generation (Jinja2 template)
- U7: Deploy + polish — Dockerfile, fly.toml, README, hex audit (all raw hex replaced with constants/CSS vars)
- Shipping quality check: ruff format (23 files), ruff lint (68 issues → 0), full test suite green

### Session 4 — Performance refactor + bug fix (2026-06-15)
- **Root cause of empty charts:** ~2M weekly scan rows processed per callback caused timeouts
- **Root cause of column collision:** door_count.py merged AUTH (has `retailer_id`) with STORE_INFO (also has `retailer_id`), creating `retailer_id_x`/`retailer_id_y` suffixes → KeyError on groupby
- Created `app/data.py` — centralized data loading with quarterly pre-aggregation (~2M → ~150K rows)
- Added parquet disk caching in `.cache/` (startup: 15s → 1.3s on warm cache)
- Rewrote `app/calculations.py` — new API using pre-aggregated SCAN_QUARTERLY
- Updated all 4 view modules to import from `app.data` instead of cinderhaven_store_universe directly
- Fixed column collision: merge only `retailer_name` from STORE_INFO (not `retailer_id`)
- Disabled Werkzeug reloader for local dev (`use_reloader=False`)
- Verified all 4 tabs render correctly with data via preview tool

## Known visual bugs (from browser QA)

These three bugs were identified at the end of session 4 and need fixing before redeploy:

1. **Purple accent on tabs and dropdowns** — Dash default purple is used for the active tab underline and dropdown selection highlights. Should be Chicago Navy (`#1f2e7a`). Fix location: `assets/style.css` — need CSS overrides for `.custom-tab--selected` border/underline color and Dash dropdown `.Select-value` / `.Select-option.is-focused` styles.

2. **Chart legend overlaps chart title** — On the "Authorized vs Carrying Doors by Retailer" chart, the legend (positioned `y=1.02` above the chart) overlaps or collides with the chart title. Fix location: `app/views/door_count.py` `_build_retailer_chart()` — adjust `margin.t` or legend positioning in the `economist_layout()` call.

3. **Content wrapping / layout issues** — Needs investigation at 1440px and 375px. Possibly the filter bar dropdowns or chart containers not respecting the max-width container.

## What's next

1. Fix the 3 visual bugs above
2. Redeploy to Fly.io (`fly deploy`)
3. Browser QA at 1440px and 375px
4. Run `/ce:review` (reviewer ensemble)

## Key files

- Requirements: `docs/brainstorms/2026-06-15-door-math-requirements.md`
- Plan: `docs/plans/2026-06-15-door-math-plan.md`
- Canonical data: `C:\Users\mssha\projects\active\datasources\cinderhaven-data-platform\CINDERHAVEN_CANONICAL.md`
- Lailara frame kit: `C:\Users\mssha\projects\active\lailara-frame\`
- Design system: `C:\Users\mssha\projects\published\lailara-design-system\LAILARA_DESIGN_SYSTEM.md`

## Architecture (post-refactor)

- `app/data.py` — centralized data loading + pre-aggregation (SCAN_QUARTERLY, LAST_SCAN, STORE_INFO, AUTH, etc.)
- `app/calculations.py` — metric functions using pre-aggregated data (calc_penetration_rate, calc_acv_pct, calc_tdp)
- `app/views/` — 4 view modules, all import from app.data and app.calculations
- `.cache/` — parquet cache for pre-aggregated frames (gitignored)
