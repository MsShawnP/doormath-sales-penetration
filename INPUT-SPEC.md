# Door Math — Client Data Input Specification

Door Math measures **distribution penetration** (what share of authorized
item-store pairs are actually scanning) and ranks the **weeks-silent** exceptions
(authorized pairs that have gone quiet). It consumes the same canonical POS
contract as the rest of the sales-penetration family (`lailara_engagement.pos`):
weekly **scans**, the **authorization** log, and the **store** dimension.

Column names below are canonical; map your headers in `engagement.yml` under
`columns:`. Identifiers are read as **text**. A missing required column yields a
branded **Data Readiness Report**, not a result.

Door Math counts distribution — it needs **units**, not dollars — so
`dollars_sold` is optional here.

## §Scans — weekly POS scan movement (required)
| Column | Type | Required | Used for |
|---|---|---|---|
| `store_id` | identifier (text) | **required** | the store side of each pair |
| `sku` | identifier (text) | **required** | the item side of each pair |
| `week_ending` | date | **required** | last-scan date; weeks-silent by date arithmetic on the declared grid |
| `units_sold` | number ≥ 0 | **required** | a pair "scans" in a week when units_sold > 0 |
| `dollars_sold` | number ≥ 0 | optional | not used by penetration; accepted if present |

## §Authorizations — the distribution log (required)
| Column | Type | Required | Used for |
|---|---|---|---|
| `sku` | identifier (text) | **required** | authorized item |
| `store_id` | identifier (text) | **required** | authorized store |
| `authorized_date` | date | **required** | never-scanned weeks-silent is measured from here |
| `deauthorized_date` | date | optional | blank = still authorized |

## §Stores — the store dimension (required)
| Column | Type | Required | Used for |
|---|---|---|---|
| `store_id` | identifier (text) | **required, unique** | the store key |
| `retailer_id` | identifier (text) | **required** | retailer grouping |
| `chain_name` | string | **required** | banner label on the deliverable |
| `region` | string | **required** | region label |
| `state` | identifier (text) | required (blanks tolerated) | rollup |
| `volume_tier` | string | **required** | tier label |

## Required declarations (`basis:`)
- **`week_convention`** — `iso_week_ending_sunday` | `week_ending_saturday` |
  `retail_454`. Every `week_ending` is validated to fall on the declared weekday.
  Weeks-silent is computed by **date arithmetic** (`(as_of − last_scan) // 7`),
  not ISO-week-number subtraction, so the year-boundary off-by-one that the demo
  once had cannot occur in client mode.
- **`silence_threshold_weeks`** (optional, default 4) — a pair is an exception
  once it has been silent longer than this.

The scans grain `(store_id, sku, week_ending)` is validated unique and
`deauthorized_date >= authorized_date` is validated.

## Column mapping (`engagement.yml`)
```yaml
client: {name: Your Brand}
engagement: {id: YB-2026-08}
as_of_date: 2026-06-27
basis:
  week_convention: week_ending_saturday
  silence_threshold_weeks: 4
inputs:
  scans: client-data/scans.csv
  authorizations: client-data/auth.csv
  stores: client-data/stores.csv
columns:
  store_id: "Store #"
  sku: "Item Code"
  week_ending: "Week Ending"
  units_sold: "Scan Units"
  authorized_date: "Auth Date"
```
