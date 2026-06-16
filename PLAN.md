# Door Math — Plan

**Tier:** Medium
**Status:** Active — Rounds 1–4 visual polish complete. Ready for `/ce:review` then redeploy.

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
