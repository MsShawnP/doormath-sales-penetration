# Door Math — Plan

**Tier:** Medium
**Status:** Active — review pass complete (2026-07-27), 23 commits on `main` not
yet deployed. Deploy first. Revenue framing blocked pending a decision.

## Implementation Units (from plan doc)

### U1: Store Universe Package
- [x] 640 doors across 6 retailers, volume tiers, regions
- [x] Authorization matrix with deliberate gaps
- [x] POS scan data (Q1 2024–Q4 2025 weekly)
- [x] Slow-leak story (CHP-DG-003 dramatic, CHP-SC-007 subtle)
- [x] Canonical validation tests

### U2: App Shell + Brand Frame
- [x] constants.py (palette + semantic aliases + DEMO_AS_OF_DATE)
- [x] Vendor lailara-frame (CSS + 4 woff2 fonts + wrap function)
- [x] Tab navigation (4 tabs) + shared filter bar + dcc.Store
- [x] wsgi.py entry point (not app.py)
- [x] Delete old scaffold (pages/, data/synthetic.py, old app.py)

### U3: Door Count View
- [x] Hero metric (% addressable doors carrying)
- [x] Horizontal grouped bar chart (authorized vs carrying by retailer)
- [x] Product line stacked bar
- [x] Click-to-pin dark callout cards
- [x] Auth gap narrative annotations

### U4: Trends View
- [x] ACV% and TDP line charts by quarter
- [x] Slow-leak annotations (CHP-DG-003, CHP-SC-007)
- [x] Snap-to-nearest click targets with tooltip
- [x] calculations.py (centralized metric computations)

### U5: Exceptions View
- [x] AG Grid table (10 columns, sort by weeks silent)
- [x] Row selection → inline detail card
- [x] CSV export only (no JSON)
- [x] Summary stats + narrative annotation

### U6: Scorecard + PDF
- [x] Screen scorecard (live filter update)
- [x] WeasyPrint PDF generation (Jinja2 template)
- [x] Letter portrait, Lailara print rules

### U7: Deploy + Polish
- [x] Dockerfile (WeasyPrint deps, store universe package)
- [x] fly.toml (1024MB, stop, health check)
- [x] Mobile responsive pass + manual checklist
- [x] Accessibility pass + manual checklist
- [x] README per Lailara template

## Improvement History

### 2026-07-27 — Improvement pass
- **Trigger:** user-initiated (`/improve`, code review, UI review)
- **What was reviewed:** all app code, calculations and metric definitions,
  the design system against the live-rendered page, tests, dependencies,
  workflow files, repo hygiene, and a 30-second CEO/CFO comprehension read.
  7-reviewer audit workflow with adversarial verification — 61 raw findings,
  58 surviving, 3 refuted.
- **What was fixed:** 6 metric/reporting defects (gap-chart labels misreading as
  wrong numbers, Top Exceptions ranked by a constant, PDF caption naming the
  wrong metric, phantom 0.0% rows, TDP ignoring the item filter, TDP chart
  plotting nudged values); stale pinned callouts; a cache key blind to every
  generator change; the TDP/ACV% documentation mismatch; 7 design-system
  violations (Times New Roman fallback, missing canvas, Plotly Open Sans in all
  chart text, vertical gridlines, 4px radius, off-palette borders, raw hex);
  3 framing gaps (page title sized below body text, gap cards never totalling,
  an unexplained "widest gap" badge); and hygiene — ruff, a fresh clone that
  could not install, dependency declarations, dead code, tracked screenshots,
  .dockerignore, gitleaks. Tests 157 → 179, including batch-vs-reference parity
  proved by fault injection.
- **Deferred:** revenue framing and the hero reframing (blocked on a decision
  about whether the store universe gains a price field) — **resolved and shipped
  2026-07-29**, see below; PDF-under-test via CI; dependency lockfile;
  MAX_CONTENT_LENGTH; PDF executor saturation; unreachable empty state;
  empty-filter semantics differing on Trends; duplication clusters.
  All listed under "Known-but-unfixed" in HANDOFF.md.
- **Next review:** 2026-08-24

### 2026-07-29 — Ship, then font integrity
- **Trigger:** continuation of the 2026-07-27 pass — deploy the fixes, then
  resolve the deferred revenue decision.
- **What was fixed:** the revenue-at-risk callout, driven by a visible
  user-editable $/item/store/week assumption with **no change to the store
  universe** (the data has no price, velocity, or unit count — `scanned` is a
  boolean); gap cards now state the per-store reading behind each pair count, so
  "999" sanity-checks itself; the PDF actually embeds Playfair Display and Source
  Sans 3 instead of falling back to DejaVu/Liberation, fits one page, and its
  footer separator renders; and **Source Sans 3 "regular" was ExtraLight
  outlines** — not a mislabel, proved by advance width — now replaced from
  `@fontsource` with a test asserting every face is the weight it claims.
  Deployed as Fly v20 and verified against the live site.
- **Verification:** PDF rendered in the production Docker image (WeasyPrint
  cannot run on Windows, which is what hid the font fallback); 179 tests pass;
  every ui-review DOM, layout and design check green on production.
- **Opened, not closed:** the ExtraLight file is in **34 repos portfolio-wide**.
  Door Math is fixed; 33 are not, 9 of them linked from lailarallc.com/work. The
  sweep is fully scoped with a validated detector at `tools/face_audit.py`, but
  execution belongs to `lailara-frame` first and is not Door Math work.
- **Next review:** 2026-08-24 (unchanged)
