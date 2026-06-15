# Door Math — Distribution Penetration Tracker

Of the stores that could carry an item, how many actually do — and is that number growing or quietly eroding? Distribution penetration is the denominator for everything downstream: velocity, household penetration, repeat rates. Most brands cannot state theirs accurately by retailer. Door Math tracks door counts, ACV%, TDP, and the gap between authorized and scanning stores.

## Cinderhaven context

Built on the Cinderhaven synthetic dataset — a ~$25M specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

## What it finds

- **% of addressable doors carrying** — authorized doors / total addressable doors, by item
- **Unweighted distribution** — raw % of stores carrying
- **Weighted distribution (ACV%)** — % of all-commodity volume flowing through carrying stores
- **TDP (Total Distribution Points)** — sum of ACV% across items; captures breadth and depth
- **Authorized vs scanning gap** — the delta between "retailer says yes" and "the shelf says yes"

## Stack

- Python 3.11+
- Dash 3.x (Plotly)
- dash-bootstrap-components
- dash-ag-grid
- pandas
- Gunicorn
- Fly.io

## Data contract

**Canonical baseline:** 50 SKUs · 5 product lines (AS·PS·SC·DG·SB) · 6 retailers (Walmart·Costco·Whole Foods·Sprouts·Kroger·Regional Group) · 10 channels (6 retail + UNFI·KeHE·DPI + DTC)

Extended with a synthetic store universe: ~600 doors across 3 banners with volume tiers, an authorization matrix with deliberate gaps, and a slow-leak distribution story.

## Run

```
git clone <repo-url>
cd doormath-sales-penetration
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open http://localhost:8050

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
