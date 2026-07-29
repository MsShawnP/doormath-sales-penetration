# Door Math — Decisions

## 2026-07-29 — Font integrity and the cross-repo sweep

**Detect by weight, verify by hash, never detect by hash.**
A font file is affected when its `OS/2.usWeightClass` disagrees with the
`font-weight` its `@font-face` declares. That is the defect, and it catches the
whole class — ExtraLight in the 400 slot, a Light 300, or a correct file simply
declared wrong. The four pinned `@fontsource` md5s are the *verification* target
after replacement. **Do not** build a known-bad hash list and scan for it: at
least three bad variants exist and the list is not closed, so a hash-based
detector produces false confidence. The two directions are not symmetric.

**Font binaries and stylesheet changes never ship in the same commit.**
A binary swap is hash-verifiable and fails visibly. A CSS change is semantic,
layers against each consumer's own overrides, and can fail in one tool and not
another. Bundled, a bad result has two candidate causes and no clean bisect —
and this project has already seen the worse version of that, where the font
files were fine and the `font-family` declaration was the defect. **Do not**
fold the frame's v1.3.0 base layer, or a new Sans 500 face, into the font sweep,
even while editing the same directory.

**Every vendored font face carries a test asserting its file is the weight it claims.**
`tests/test_pdf_fonts.py::TestFontFilesAreTheWeightTheyClaim` asserts declared
weight equals `usWeightClass`, that no two weights share identical outlines, and
that heavier weights are wider. It needs only fontTools, so it runs on Windows
where WeasyPrint cannot. This bug class has now shipped twice — a bold face that
was a byte-copy of the regular (`c60a37b`), then ExtraLight outlines in the
regular slot (`ed2815f`) — and neither was visible by filename or by eye.
`tools/face_audit.py` is the same check as a CLI over arbitrary repos.

**Revenue at risk is a stated assumption in the UI, never a data field.**
The store universe carries no price, velocity, or unit count — `scanned` is a
boolean, so the data cannot say how much sold, only whether it sold. Revenue at
risk is therefore computed from a visible, user-editable rate, labelled as an
assumption, defaulted sensibly. **Do not** add price or velocity fields to
`cinderhaven-store-universe` to make this number "real"; the package feeds all
five Cinderhaven tools and the assumption belongs to the reader, not the dataset.

**A pair count is always shown with its per-store reading.**
"999 pairs not scanning" is arithmetically right and intuitively meaningless — it
reads as implausible to someone who knows the account, because "item-store pair"
is an analyst unit. Each gap card states the count *and* the median items missing
per store across the door count, so the headline number sanity-checks itself.

**For a multi-repo sweep, publish the discovery rule, not a list of repos.**
Three scans under-counted before settling, because each hardcoded list inherited
the bug of the scan that produced it. The handoff specifies the detector, its
exclusions (`node_modules`, `renv`, `_freeze`, `.quarto`, `output`, `*_files`),
and two control repos with independently established answers — clean and affected
— so a wrong answer is distinguishable from a wrong detector. **Do not** hand a
downstream session a repo list as the work definition.

## 2026-07-27 — Revenue at risk

**Revenue at risk is a stated assumption, never inferred from the data.**
The gap was reported only in item-store pairs, which no executive can price.
Rather than add a price or velocity field to the store universe — which would
trigger the data change protocol below and propagate across all five Cinderhaven
tools — the rate is supplied by the reader through a visible input on the Door
Count tab. Confirmed against the schema before building: `stores` carries
store_id / retailer_id / retailer_name / region / volume_tier, `auth` carries
sku_id / store_id / retailer_id / authorized / authorized_date, and `scans`
carries sku_id / store_id / week / **scanned as a boolean**. The data cannot say
how much sold, only whether it sold. That is precisely why the rate has to come
from outside it. No file under `packages/` was touched.

**The rate is $/item/store/week, overruling an earlier $/door/week.**
The gap is counted in item-store pairs, so a per-door rate is a unit mismatch:
applying it literally means collapsing to the 616 doors with any gap and charging
each the same regardless of depth, so a door missing 14 of 40 items and one
missing 1 of 22 carry identical risk. That contradicts the tool's own thesis —
depth is half of what Door Math measures. Both units can express the same total
($15/item/store/week and $78.92/door/week both give $2.5M today); they diverge
exactly when the mix changes, which is when the tool should notice. Default $15.

**The assumption is printed inline with the figure, in both surfaces.**
On screen the input carries its unit in the label and an italic note states the
figure is not measured. In the PDF the two are a single sentence — "≈$2.5M/yr
revenue at risk on 3,241 authorized pairs not scanning — assumes
$15/item/store/week" — so the number cannot be quoted without the rate that
produced it. In the PDF it sits below the distribution tables, above Top
Exceptions, at 9.5pt with a 1pt Red-42 left rule: secondary by construction,
never the hero. A test asserts that placement so a later edit cannot promote it.

**The rate lives in a shared `dcc.Store`, and the input persists.**
Tab content is swapped, so `dc-rev-rate` is not mounted when the Scorecard builds
its PDF — a `State` reference to it would fail. The store mirrors the value for
the PDF callback, and `persistence="session"` on the input stops the assumption
silently resetting to the default when the reader navigates away and back.

**The PDF's gap is derived from the rows the PDF prints.**
`gap_pairs` is summed from `retailer_rows`, not recomputed, so the printed money
figure cannot drift from the printed distribution. Verified equal to the Door
Count gap under three filter states (3,241 / 999 / 73).

## 2026-07-27 — Review pass (improve + code review + UI review)

**TDP and ACV% keep their different bases; the documentation was wrong.**
The glossary and the TDP chart footnote both claimed "TDP is the sum of ACV%
across all your items". Measured at Walmart Q4 2025: TDP 21.77, sum of the app's
per-SKU ACV% 39.63. `calc_tdp` divides by the weight of every addressable store
counted once; `calc_acv_pct` divides by the weight of every authorized pair, so a
store counts once per authorized item. `calc_tdp` is the standard Total
Distribution Points definition, and the pair-level ACV% base is a deliberate
choice from Session 9. Both are right on their own terms, so the fix was to
restate the docs, not to change a metric. Both entries now say explicitly that
the two do not sum to one another.

**Top Exceptions ranks by silent-store count, not max weeks silent.**
Every SKU has at least one pair that never scanned, and never-scanned pairs get
the 104-week sentinel, so `max(weeks_silent)` was 104 for all 50 SKUs — the sort
was a no-op and `.head(10)` returned the alphabetically-first ten SKU codes.
Ranking by silent-store count matches the Exceptions tab's own grouping, so the
three surfaces now agree. Kept the 104 sentinel: the data window is ~104 weeks,
so "silent for the whole window" is a defensible reading. It just cannot be a
ranking key.

**The TDP chart plots real values; position-dodge removed entirely.**
The dodge nudged plotted y up to 1.5 points off while labels, hover text and the
median line used true values, so a retailer below the median could be drawn above
it. Deliberately did not take the alternative fix of re-sorting lanes by the drawn
quarter — FAILURES.md records that exact approach was tried and reverted for
producing artificial line crossings. Plotting the truth makes lane assignment
moot. Retailers stay distinguishable via the unique colour, dash and marker each
already has from Session 10.

**Chart typography is fixed by overriding Plotly's container, not its text.**
Plotly injects a stylesheet setting `.plotly` to Open Sans, and SVG `<text>`
inherits it. An `!important` on `text` would work but would also beat the chart
title's inline Playfair and turn every title sans. Overriding the container lets
inline styles keep winning where Plotly does set them.

**The frame gains a base layer; upstream must be re-vendored.**
`lailara-frame.css` styled `.lailara-page` but never `body`, so unstyled text fell
back to Times New Roman and the warm canvas did not cover the page. This is a
frame defect, not a Door Math one — every Lailara tool vendoring v1.2.0 or
earlier has it. Bumped to v1.3.0 here; the upstream frame kit still needs the
same change. Set no `font-size` at the frame level: tools size their own text and
imposing the 17px body step would reflow every consumer.

**The gap bar is Chicago navy (#1f2e7a), not London-70 grey.**
Correcting the record. The 2026-07-02 entry below says the gap bar reverted to
London-70 grey for colour-vision safety, and FAILURES.md said the same, but the
shipped code uses `LL_CHICAGO` navy against HK-35 teal — distinguished by hue
rather than red/green, so still CVD-safe. The docs described a state the code left
behind.

**Filter changes clear chart pins rather than recomputing the callout.**
The callout callback reads `filter-state` as State, which does not trigger, so
pinned cards kept showing the previous selection's numbers. Clearing the pin keeps
the existing callback graph intact — the pin store stays the single trigger for
the callout, and the chart figure keeps one owner per interaction. Matches what
the plan document already specified.

**The cache key hashes generation inputs by value.**
Hashing collection lengths could not see a changed seed, scan rate, auth rate,
volume-tier weight or slow-leak curve — all of which leave every length identical
— so the app silently served pre-aggregates built from data that no longer
existed. No generator logic was touched, only how the app fingerprints it.

**The hero number's 10px line-box overflow is left as-is.**
`ui-review` reports it, but no ancestor clips it and the glyphs paint complete —
verified against the rendered page. Growing the frame's line-height would shift
vertical rhythm for every tool vendoring it to fix a box-model report with no
visible symptom.

**Screenshots are untracked; gitleaks allowlisting is per-rule.**
`screenshots/` is regenerable ui-review output that nothing links to, so it is
gitignored rather than versioned. The gitleaks allowlist for `.env.example` is
scoped to the postgres rule alone, not global, so every default rule still scans
that file — a real key pasted there is still caught.

## 2026-07-02 — Design-system compliance

**All hex values sourced from `lailara_palette` package, not hardcoded.**
Vendored `lailara-palette` (v2.1.0) into `packages/lailara-palette/`. Replaced all ~40 hardcoded hex values in `app/constants.py` with imports. Semantic aliases (`ACCENT`, `DELTA_POS`, `GAP_BAR`, etc.) still exist but now reference palette tokens, not raw strings. Single source of truth for the entire Cinderhaven suite.

**Gap bar is not Tokyo-70.** *(Superseded — see the 2026-07-27 correction above.
The shipped colour is Chicago navy `#1f2e7a`, not the London-70 grey this entry
originally recorded.)*
Tried Tokyo-70 (#e68a9a, rose/berry) for the authorization gap bar — visually distinct from HK teal, reads as "mild negative." Reverted because the gap chart uses HK-35 (teal) for scanning bars alongside the gap bars, and teal-vs-rose is unreadable under red/green color-vision deficiency (deuteranopia/protanopia). Accessibility trumps semantic color.

**`economist_layout()` uses one-level deep merge, not shallow `dict.update()`.**
`defaults.update(overrides)` shallow-replaced dict keys like `title.font`, losing the base chart-title font settings (family, size, color) whenever an override only set `title.text`. Fixed with a one-level deep merge that preserves nested dict values not explicitly overridden.

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

## 2026-06-16 — Code review fixes

**Batch scorecard computation (batch_acv_by_product_line + existing batch functions).**
Scorecard `_compute_scorecard_data()` was calling `calc_acv_pct` and `calc_tdp` per retailer (6×) and per product line (5×), plus `filter_auth` and `carrying_in_quarter` per entity — ~30 individual queries per render. Replaced with `batch_acv_by_retailer` + `batch_tdp_by_retailer` + new `batch_acv_by_product_line` + single `filter_auth` + groupby — ~5 queries total. This extends the batch pattern established in Session 10 for trends.

**Unfiltered data callout pattern.**
When `retailers=[]` or `product_lines=[]`, `filter_auth` treats empty lists as "no filter" and returns all data. Rather than changing `filter_auth` semantics (which would break existing callers), added `unfiltered_data_callout()` in `components.py` that detects empty filter lists and shows an informational annotation. Applied to all 4 tabs.

**Non-blocking PDF generation with ThreadPoolExecutor.**
WeasyPrint PDF rendering is CPU-bound and blocks the Gunicorn worker thread. Two-pronged fix: (1) switched Dockerfile from sync workers to `gthread` with 2 threads (threads share memory, no extra cost on 1024MB VM), (2) wrapped `HTML(string=...).write_pdf()` in a ThreadPoolExecutor with 30s timeout for defense-in-depth. The executor has `max_workers=1` since concurrent PDF renders would OOM.
