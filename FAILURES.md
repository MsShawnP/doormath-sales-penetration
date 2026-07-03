# Door Math — Failures

## 2026-07-02

**Tokyo-70 gap bar failed accessibility under red/green CVD.**
Used Tokyo-70 (#e68a9a, rose/berry) for the authorization-vs-scanning gap bar, paired with HK-35 (teal) for the scanning segment. Looked great under normal vision — two distinct hues for two semantically different segments. But teal and rose collapse to the same muddy olive under deuteranopia/protanopia, making the gap invisible. Reverted to London-70 (neutral grey), which is universally distinguishable. Lesson: when two bar segments sit side by side, check the pair under simulated CVD before committing, not just individually.

**`economist_layout()` shallow merge silently dropped chart title fonts.**
`defaults.update(overrides)` in `charts.py` replaced the entire `title` dict when a caller passed `title={"text": "My Chart"}`, losing the base font settings (`family`, `size`, `color`). Charts rendered with Plotly defaults (small, wrong font). Not caught until DOM-eval during the design-system compliance pass because the visual difference was subtle on some charts. Lesson: when a function merges a nested config dict, verify it's deep-merging, not shallow-replacing.

## 2026-06-15

**app.py / app/ Python import collision (caught in plan review, not production).**
The scaffold had `app.py` at root and planned to create `app/` as a package. Python resolves the package directory over the file, so `gunicorn app:server` would import the package's `__init__.py` instead of the WSGI entry point. This is a production crash, not a subtle bug. Fix: rename entry point to `wsgi.py`. This exact issue was already documented in velocity-tool's FAILURES.md — the plan review's feasibility agent caught it before implementation.

**Callback timeouts from unoptimized scan data (found in browser QA).**
All 4 view modules loaded their own copy of ~2M weekly scan rows and processed them per callback invocation. On Fly.io (1024MB), callbacks timed out before completing, producing "server did not respond" errors. On the client side this looked like (a) design system not loading (page hung before CSS rendered) and (b) charts empty on filter selection. Root cause was pure performance — not a CSS or filter bug.

**Position dodge per-quarter sort causes artificial line crossings.**
First implementation of `_dodge_overlapping()` sorted cluster members by their value at each quarter independently. When two retailers' values are close but swap relative position between quarters, they get different lanes at each x-position — creating artificial X-pattern crossings that don't exist in the real data. Fix: sort cluster members by their *mean* value across all quarters, giving each retailer a consistent lane. Lesson: when nudging overlapping data series for visual clarity, stable lane assignment matters more than per-point accuracy.

**Re-exporting SKU_NAMES through app/data.py flagged by ruff F401.**
Tried to centralize all data imports through `app/data.py` by re-exporting `SKU_NAMES` there. Ruff flagged it as an unused import (F401) because `app/data.py` itself doesn't use the symbol — it only re-exports it. The `__all__` workaround would have been artificial. Fix: consumers import `SKU_NAMES` directly from `cinderhaven_store_universe.constants`, matching the existing pattern in `filters.py`. Lesson: don't force a "single hub" import pattern when the linter enforces used-only imports; follow the existing convention instead.

**Preview screenshot timeout on Plotly-heavy Dash pages.**
`preview_screenshot` timed out at 30s repeatedly on the Door Count tab (2 Plotly charts with stacked bars and text annotations). The page was fully loaded and interactive — `preview_eval` and `preview_snapshot` both worked. Workaround: verify chart behavior via `preview_eval` (inspect `chart.data` for `textposition` arrays) and `preview_snapshot` (accessibility tree for rendered text). Lesson: for Plotly-heavy Dash apps, don't rely on preview screenshots for verification — DOM inspection is faster and more reliable.

**CSS overflow fix targeted wrong element (dropdown-wrap instead of filter-group).**
Initial attempt to fix the 37px filter bar overflow added `overflow: hidden` to `.dropdown-wrap` (the wrapper around the dropdown + summary overlay). This didn't work because the overflowing element was Dash's internal `.dash-dropdown-focus-target` input, which is a child of the dropdown component itself — not inside `.dropdown-wrap`. The fix needed to be on `.filter-group` (the parent containing both the label and the dropdown). Lesson: when debugging CSS overflow, measure at every DOM level to find which element is the actual source before applying containment.

**pandas merge column collision (retailer_id).**
`door_count.py` merged AUTH (which has `retailer_id`) with STORE_INFO (also has `retailer_id`) on `store_id`. pandas silently renamed to `retailer_id_x` / `retailer_id_y`. The subsequent `groupby(["retailer_id", ...])` threw KeyError. Fix: only merge `retailer_name` from STORE_INFO since AUTH already has `retailer_id`. Lesson: when merging DataFrames that share column names beyond the join key, be explicit about which columns to pull.
