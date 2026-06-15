# Door Math — Distribution Penetration Tracker

**Live:** https://doormath.lailarallc.com

Of the stores that could carry an item, how many actually do — and is that number growing or quietly eroding? Distribution penetration is the denominator for everything downstream: velocity, household penetration, repeat rates. Most brands cannot state theirs accurately by retailer. Door Math tracks door counts, ACV%, TDP, and the gap between authorized and scanning stores.

## Cinderhaven context

Built on the Cinderhaven synthetic dataset — a ~$25M specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

## What it finds

- **% of addressable doors carrying** — authorized doors / total addressable doors, by item
- **Weighted distribution (ACV%)** — % of all-commodity volume flowing through carrying stores
- **TDP (Total Distribution Points)** — sum of ACV% across items; captures breadth and depth
- **Authorized vs scanning gap** — the delta between "retailer says yes" and "the shelf says yes"
- **Slow-leak detection** — two SKUs (CHP-DG-003, CHP-SC-007) quietly losing doors quarter over quarter without obvious signal

Four views: Door Count (current state), Trends (ACV%/TDP trajectory), Exceptions (authorized-but-not-scanning), Scorecard (one-page PDF summary).

## Stack

- Python 3.11+
- Dash 3.x / Plotly (SVG charts)
- dash-ag-grid (exception table)
- pandas / numpy
- WeasyPrint (PDF scorecard)
- Jinja2 (PDF template)
- Gunicorn
- Fly.io (1024MB, auto-stop)

## Data contract

**Canonical baseline:** 50 SKUs · 5 product lines (AS·PS·SC·DG·SB) · 6 retailers (Walmart·Costco·Whole Foods·Sprouts·Kroger·Regional Group) · 10 channels (6 retail + UNFI·KeHE·DPI + DTC)

Extended with a shared store universe package (`packages/cinderhaven-store-universe/`): 640 doors across 6 retailers with volume tiers, an authorization matrix with deliberate gaps, weekly POS scan data (Q1 2024 – Q4 2025), and two slow-leak distribution stories.

## Run

```
git clone <repo-url>
cd doormath-sales-penetration
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e packages/cinderhaven-store-universe
pip install -e ".[dev]"
python wsgi.py
```

Open http://localhost:8050

### PDF export (requires Linux system libraries)

```
pip install -e ".[pdf]"
```

WeasyPrint requires pango/cairo system libraries. On Debian/Ubuntu:

```
apt-get install libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-xlib-2.0-0 fonts-liberation
```

PDF generation works inside the Docker container. On Windows, the scorecard screen view works but PDF download is unavailable.

### Docker

```
docker build -t doormath .
docker run -p 8050:8050 doormath
```

### Tests

```
python -m pytest tests/ packages/cinderhaven-store-universe/tests/ -v
```

## Mobile testing checklist

- [ ] Tabs scroll horizontally at 375px (no vertical stack)
- [ ] Filter bar collapses — "Filters" toggle button expands full-width panel
- [ ] Charts scroll horizontally within container (min-width 600px)
- [ ] AG Grid scrolls horizontally with frozen SKU ID column
- [ ] Annotations collapse to inline icon, tap to expand, tap/scroll to dismiss
- [ ] PDF download button hidden on mobile
- [ ] Hero metric font scales (64px → 44px)
- [ ] Brand frame header wraps at narrow viewports
- [ ] No horizontal page overflow at 375px

## Accessibility testing checklist

- [ ] Tab navigation via arrow keys works (Dash built-in)
- [ ] Focus-visible outlines appear on interactive elements (2px solid)
- [ ] Charts have `aria-label` describing the data summary
- [ ] AG Grid keyboard navigation works (built-in)
- [ ] Skip-to-content link is present and functional
- [ ] `prefers-reduced-motion`: number animations snap, transitions instant
- [ ] Color is never the sole identification channel — every data point has a text label
- [ ] Contrast ratio meets WCAG AA (4.5:1 for text, 3:1 for UI components)

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
