# Door Math — Distribution Penetration Tracker

**Working title:** `door-math` (alts: `footprint`, `shelfcount`)

## Business question this tool answers

> "Of the stores that *could* carry this item, how many actually do — and is that number growing or quietly eroding?"

This is the most literal meaning of "penetration": physical presence on shelves. Before anyone talks about velocity, household buyers, or repeat rates, the item has to exist in a store. Distribution penetration is the denominator for everything downstream, and most brands can't state theirs accurately by retailer.

## Why CEOs say "penetration" and mean this

When a Walmart buyer or a CPG exec says "we need more penetration," half the time they mean door count: get into more of the 4,600 US stores, get into Neighborhood Market, get into more regions. It's the growth lever that shows up first in a sales bridge.

## Core metrics

- **% of addressable doors carrying** — authorized doors ÷ total addressable doors, by item
- **Unweighted distribution** — raw % of stores carrying
- **Weighted distribution (ACV%)** — % of all-commodity volume flowing through carrying stores. A brand in 30% of stores that happen to be the highest-volume stores has very different reach than 30% of rural low-volume doors
- **TDP (Total Distribution Points)** — sum of ACV% across items; captures both breadth (doors) and depth (items per door)
- **Authorized vs scanning** — the gap between "Walmart says yes" and "the shelf says yes." This delta is where money dies

## Inputs

- Item master (Cinderhaven canonical item list)
- Store/door list with banner, region, store volume tier
- Authorization matrix (item × door)
- POS scan data (item × store × week) — even synthetic weekly scan flags are enough

## Outputs

- Door-count dashboard by item, banner, region
- ACV% and TDP trend lines (is distribution building or bleeding?)
- Authorized-but-not-scanning exception list (feeds directly into the Void Finder tool, #5)
- One-page "distribution scorecard" suitable for a buyer meeting

## Cinderhaven angle

Cinderhaven canonical figures already define the item set. Need to add: a synthetic store universe (e.g., 600 doors across 3 banners with volume tiers) and an authorization matrix with deliberate gaps and a slow-leak story (an item losing doors quarter over quarter without anyone noticing).

## Scope notes / open questions

- Probably the simplest of the five computationally — the value is in the data model (store universe + authorization matrix), which then gets reused by tools 2 and 5
- Build the store universe generator once, version it in CINDERHAVEN_CANONICAL or a sibling file, and lock it the same way canonical figures are locked
- Decide: standalone repo or shared `cinderhaven-store-universe` package the other tools import?
