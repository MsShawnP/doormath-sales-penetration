# Door Math — Handoff

## Current phase

Review pass complete — audit, code review and UI review run, findings fixed
across 23 commits on `main`. **Not deployed.** The live site is now well behind
`main`; a deploy is the first thing the next session should do.

### Session 16 — improve + code review + UI review (2026-07-27)

**Started from:** live site 2 commits behind HEAD (Fly v18, Jul 14, built from
`8d90972`). HANDOFF was itself 12 commits stale and made three false claims —
wrong commit, "151 tests" when the suite ran 157, and "design-system compliance
at 100%" that two hardcoded colours contradicted. All corrected below.

**Ran:** a 7-reviewer audit workflow with adversarial verification (18 agents,
61 raw findings, 58 surviving), the ui-review tool against both the live site and
a local HEAD build, and a 30-second CEO/CFO comprehension read.

**Fixed — numbers the tool was reporting wrong:**
- Gap chart labels were painted over by the bars: Sprouts' 574 read as 674,
  Costco's 95 as 05, Regional Group's 315 as 815, and 4,997 / 3,920 lost their
  last digit. Two causes, both measured in rendered SVG geometry.
- Scorecard/PDF "Top Exceptions" ranked by a value identical for all 50 SKUs, so
  it printed the alphabetically-first ten. Now ranks by silent-store count and
  matches the Exceptions tab — surfaces CHP-DG-003 and CHP-SC-007, the two
  deliberate slow-leak SKUs.
- The PDF hero caption named a different metric than its number ("addressable
  doors carrying" is 100%, not 84.7%).
- Scorecard invented 0.0% rows for filtered-out product lines, then named one as
  worst-performing.
- TDP ignored the item filter on both the scorecard and the Trends chart.
- The TDP chart plotted nudged positions while labels and the median used real
  values; position-dodge removed.
- Pinned callout cards kept stale numbers after a filter change.
- The parquet cache key could not detect any generator change.
- Glossary and footnote claimed TDP sums ACV%; measured 21.77 vs 39.63.

**Fixed — design system:**
- The frame set no `body` font, so 14 visible elements rendered in Times New
  Roman, and no `body` background, so the warm canvas did not cover the page.
  Frame bumped to v1.3.0 — **the upstream frame kit still needs this change.**
- All chart text rendered in Plotly's Open Sans (74 elements) despite the figure
  spec being correct.
- Vertical gridlines on both Door Count charts; Dash's 4px radius; off-palette
  borders; the last four raw hex values.
- Hero number migrated to the frame's `.ll-headline-number`.

**Fixed — hygiene:** repo now passes `ruff check` and `ruff format`; a fresh
clone installs (lailara-palette was never installed by the README); `flask`
declared and unused `python-dotenv` dropped; dead constants and helpers removed;
1.6 MB of screenshots untracked; `.dockerignore` added; gitleaks stops flagging
its own env template.

**Tests: 157 → 179.** Added batch-vs-reference parity coverage — proved the gap
by injecting the suspected regression and watching all 130 pre-existing tests
pass blind to it.

**State:** `main` at 23 commits ahead of `origin/main`. 179 pass, 2 skip. Ruff
clean. ui-review design checks all pass except one Plotly SVG false positive.

**Then, after the revenue decision came back (Option 3):**
- Added a revenue-at-risk callout on the Door Count gap, driven by a visible,
  editable `$/item/store/week` input. Default $15 → $2.5M.
- Threaded it into the exported PDF with the assumption printed inline, below the
  distribution tables, as a secondary line rather than the hero.
- No changes to `packages/` — confirmed the schema carries no price, velocity or
  unit field, and that `scanned` is a boolean.
- The specified unit was `$/door/week`; shipped `$/item/store/week` after
  flagging it, because the gap is pair-counted and a per-door rate discards the
  depth of the gap. Decision recorded in DECISIONS.md.

**Still not done:** the hero continues to lead with 84.7% rather than the
deficit. Reframing it was not part of the revenue decision.

### Session 15 — Design-system compliance (2026-07-02)

**Started from:** Gap chart used London-70 (disabled) for gap bars, hardcoded hex values throughout constants.py.

**Did:**
- Task A: Changed gap bar color from London-70 to Tokyo-70 (#e68a9a, "mild negative"), gap label text to Tokyo-15 bold. Later reverted to London-70/DISABLED for accessibility — teal-vs-rose is unreadable under red/green color-vision deficiency.
- Task B: Vendored `lailara_palette` package (v2.1.0) into `packages/lailara-palette/`, replaced all ~40 hardcoded hex values in `app/constants.py` with imports from the package. Updated Dockerfile and pyproject.toml.
- Task C: Fixed `economist_layout()` deep-merge bug — `defaults.update(overrides)` shallow-replaced dict keys, losing chart title font settings. Implemented one-level deep-merge. Verified color roles via DOM-eval (canvas, deltas, axis text, chart titles, gridlines).
- All committed (`95f96a4`), deployed, verified with full proof report.

**State:** `main` pushed to `origin/main` (`786d2c8`). 151 tests pass, 2 skip. Deployed and healthy. All color tokens sourced from `lailara_palette`.

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

### Session 5 — Visual polish (2026-06-15)

**Fixed:**
1. **Purple accent on tabs/dropdowns** — Dash 4 uses Radix UI, not React-Select. Added CSS overrides in `assets/style.css` targeting `.tab--selected` (border-top-color), `.dash-dropdown` (outline-color), `.dash-options-list-option-checkbox` (accent-color), `.dash-options-list-option:hover` (background-color). All Chicago Navy.
2. **Chart legend/title overlap** — Increased default `margin.t` from 60→100 in `app/charts.py` `economist_layout()`. Also set explicit `margin.t=100` on door_count.py retailer and product line charts.
3. **Layout containment** — Verified at 1440px and 375px, no overflow issues found.
4. **Legend text truncation on Trends** — Changed trends layout from side-by-side (50% width each) to vertical stack (full width). Each chart now in its own `html.Div` with 40px gap.
5. **TDP y-axis range** — Removed `rangemode="tozero"` from TDP chart yaxis config so axis auto-scales to actual data range (values vary by tenths around 20-40).

**Not yet fixed:**
6. **TDP trace overlap** — Whole Foods (39.4) and Kroger (39.2) are 0.2 TDP points apart at Q4 2025, lines/markers paint on top of each other. Diagnosed: within 0.3 pts at every quarter. Solution designed (position_dodge-style visual nudging) but NOT implemented. Click-to-pin callbacks use `customdata`+`x`, never y-value, so nudging plotted y is safe. Callout card re-fetches true values from `tdp_data` dict.
7. **Product/SKU names are codes** — Store universe `constants.py` only has coded IDs like "CHP-DG-003". User wants realistic names like "Chipotle Lime Mayo". Needs a display name mapping added to the store universe package.

### Session 6 — Visual polish complete + feedback triage (2026-06-16)

**Started from:** 2 bugs remaining — TDP trace overlap, product SKU names as codes.

**Did:**
- Implemented position_dodge for TDP chart (`_dodge_overlapping()` in trends.py) — mean-based lane assignment prevents line crossings
- Added 50 realistic SKU display names to store universe constants, surfaced in dropdowns/grid/annotations
- Cleaned up unused imports (ruff compliance)
- Received and triaged 9-item feedback from screenshot review; identified critical data generation issue (#1)

**State:** Position dodge and SKU names working. All prior visual bugs fixed. 9-item feedback list identified but not started. CRITICAL: synthetic data has no deliberate authorization gaps — 100% penetration everywhere makes the tool meaningless.

**Next:** Start new session on 9-item feedback list. Priority order:
1. **[CRITICAL]** Fix synthetic data generation — add deliberate auth gaps, auth-vs-scanning gaps, slow-leak with real variance. Follow data change protocol (list files, describe changes, confirm not touching CINDERHAVEN_CANONICAL.md, wait for approval).
2. Change hero metric from any-item to SKU-level penetration
3. Fix exceptions table (remove scroll, fix Group column, fix truncation, add SKU grouping)
4. Fix legend truncation ("Whole Food" → "Whole Foods")
5. Verify ACV% lines separate after #1 [DATA ROOT]
6. Verify charts show meaningful variance after #1 [DATA ROOT]
7. Add SKU-level drill-down to Door Count view
8. Add PDF/print export button to Scorecard view
9. Add narrative annotations to Door Count, Exceptions, and Scorecard views
10. Redeploy to Fly.io
11. Run `/ce:review`

### Session 7–9 — Feedback rounds 1–2 + pair-level fix (2026-06-16)

- Fixed synthetic data (auth gaps, scanning gaps, variance)
- Changed hero to SKU-level penetration
- Exceptions table fixes (scroll, Group col, truncation, SKU grouping)
- Legend truncation fix
- ACV%/charts verified with variance
- SKU drill-down, print button, narrative annotations added
- Redeployed to Fly.io
- Pair-level fix for calc_penetration_rate and calc_acv_pct

### Session 10 — Rounds 3+4 visual polish (2026-06-16)

**Round 3 fixes:**
- Legend below all charts (y=-0.12 to -0.15), no overlap with title
- `entrywidthmode="fraction"` — full legend text, no truncation
- Y-axis auto-scale via `_auto_y_range()` with 15% padding
- Retailer chart replaced with stacked gap chart (scanning + gap segments)
- Hero baseline fixed with CSS class `hero-number`
- ACV% lines differentiated (unique color + dash + marker per retailer)
- Purple removed — comprehensive CSS overrides for Dash dropdowns, tabs, AG Grid

**Round 4 fixes:**
- Debug toolbar disabled (`debug=False`, opt-in via `DASH_DEBUG=1`)
- Trends performance: `batch_acv_by_retailer()` + `batch_tdp_by_retailer()` — 2 batch ops instead of 96 individual calls
- Scorecard Top Exceptions deduped by SKU (store count + retailer list)
- Exception Detail columns: wider minWidth, tooltips enabled
- Annotation accent bar color corrected from CARD_BG to GRIDLINE
- Bar label font bumped 11→12px

**Verified:** ACV% values range 68–95% (pair-level working). No debug toolbar. 122 tests pass, ruff clean.

**Committed:** `3bbc2c4` on main.

### Session 11 — Polish round (2026-06-16)

**Started from:** Rounds 3+4 complete. Two polish items: gap chart label collisions, scorecard repetitive retailer list.

**Did:**
- Fixed gap chart label collisions — `textposition="outside"` when gap segment < 15% of chart x-range, `cliponaxis=False`, right margin 20→100px
- Fixed scorecard Top Exceptions — "All retailers" when SKU appears at every retailer, individual names for proper subsets
- Made wsgi.py read PORT from env for preview server compatibility
- Committed, pushed, deployed to Fly.io

**State:** App deployed. All visual polish items resolved. 122 tests pass, ruff clean. No known bugs.

**Next:** Run `/ce:review` (code review ensemble), then `/ce:compound` to extract learnings.

### Session 12 — Code review + all fixes (2026-06-16)

**Started from:** App deployed, all visual polish resolved. Ran `/ce:review`.

**Did:**
- Code review ensemble (9 agents, 21 findings): 14 safe_auto applied, 7 manual fixes implemented
- #1 (P1): Input validation on `quarter_to_weeks()` — format, range, year checks
- #2 (P1): `unfiltered_data_callout()` across all 4 tabs — warns when empty filters default to all data
- #3 (P2): Warning log in `quarters_in_range()` catch block
- #14 (P2): `dcc.Loading` spinner on exceptions AG Grid
- #15 (P2): Median traces in trends charts get legend entries + hovertemplate
- #16 (P1): Non-blocking PDF via ThreadPoolExecutor + 30s timeout; Dockerfile switched to gthread workers
- #18 (P2): `batch_acv_by_product_line()` + scorecard rewrite from ~30 queries to ~5 batch ops

**State:** All 122 tests pass, ruff clean. All 21 review findings resolved. Ready to deploy + compound.

**Next:** Deploy with review fixes, then run `/ce:compound` to extract learnings.

### Session 13 — Prospect readiness (2026-06-16)

**Started from:** Code review complete, all findings resolved. Tool functionally complete but needed prospect-facing framing.

**Did:**
- Added intro section above tabs: H1 "Distribution Penetration Tracker" + one-paragraph Cinderhaven/synthetic data explanation
- Fixed filter dropdown truncation: CSS overlay shows "All retailers" / "All product lines" when all are selected, hides individual chips via `:has()` selector + Dash className callback
- Set up `doormath.lailarallc.com` custom domain: CNAME + ACME challenge in Cloudflare, Fly.io cert added (validation pending DNS propagation)
- Identified portfolio card needs adding to lailarallc.com `/work` page (separate repo)

**State:** Intro + filter fix verified in preview (122 tests pass, ruff clean). Custom domain DNS records created, cert validating. Portfolio card not yet added (separate repo at `C:\Users\mssha\projects\reference\lailara-website`).

**Next:** Verify `doormath.lailarallc.com` cert issued. Add portfolio card to lailarallc.com. Deploy review fixes + prospect readiness changes to Fly.io. Run `/ce:compound`.

### Session 14 — UI review + layout fixes + deploy (2026-06-19)

**Started from:** Visual polish round committed but not deployed (v5 stale by 3 commits). UI review identified 3 actionable layout issues.

**Did:**
- Diagnosed intro heading missing on live site as stale deployment (v5 didn't include `9190ca4`)
- Fixed filter bar 37px overflow — Dash internal `.dash-dropdown-focus-target` renders at 177px inside 140px groups; added `overflow: hidden` to `.filter-group` and constrained `.filter-summary` with `right: 30px` + text-overflow ellipsis
- Container 13px overflow resolved as side effect of filter fix
- Deployed to Fly.io (v6), verified all 3 items via ui-review tool (8 pass, 16 noise failures from Plotly SVG labels)

**State:** App deployed at v6. All layout issues resolved. 122 tests pass, ruff clean. Custom domain cert status unknown.

**Next:** Run `/ce:compound` to extract learnings. Verify `doormath.lailarallc.com` cert. Add portfolio card to lailarallc.com.

## What's next

1. **Deploy.** `main` is 23 commits ahead of the live site, and everything above
   — the misread chart labels, the wrong PDF caption, the alphabetical Top
   Exceptions — is still live for prospects until it ships.
2. **Two open questions on the revenue callout.**
   - The **on-screen Scorecard does not show it** — only the Door Count tab and
     the exported PDF do. Since the screen scorecard otherwise mirrors the PDF,
     printing carries a line the preview does not. One line to add if that
     divergence is unwanted; left alone because the instruction named the PDF.
   - **The hero still leads with 84.7%**, which reads as good news when the story
     is the 3,241 pairs producing nothing. Reframing it was not part of the
     revenue decision.
3. **Re-vendor the frame upstream.** `lailara-frame.css` v1.3.0's base layer fixes
   a defect every Lailara tool on v1.2.0 or earlier inherits (Times New Roman
   fallback, missing canvas). The fix currently exists only in this repo's
   vendored copy.
4. Verify `doormath.lailarallc.com` cert issued (`fly certs check doormath.lailarallc.com -a doormath-sales-penetration`)
5. Add portfolio card to lailarallc.com `/work` page (in `lailara-website` repo, `engagements` array in `site/src/app/work/page.tsx`)
6. Run `/ce:compound` to extract learnings

### Known-but-unfixed

From the audit, deliberately deferred rather than missed:
- PDF generation has never run under test on any machine — both real-engine
  tests skip on Windows and there is no CI. Needs a `docker run … pytest` step.
- No dependency lockfile and no upper bounds except WeasyPrint, so rebuilds are
  not reproducible.
- Flask's `MAX_CONTENT_LENGTH` is unset on a 1 GB VM.
- One stuck PDF render disables PDF export until the container restarts.
- The empty-state message and its Reset button are unreachable code.
- Empty retailer filter means "show everything" on three tabs and "show nothing"
  on Trends.
- Several duplication clusters (`_gap_card` vs `stat_card`, the two scorecard
  tables, the two chart-pin callbacks, the PDF context built twice).

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
