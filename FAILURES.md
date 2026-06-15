# Door Math — Failures

## 2026-06-15

**app.py / app/ Python import collision (caught in plan review, not production).**
The scaffold had `app.py` at root and planned to create `app/` as a package. Python resolves the package directory over the file, so `gunicorn app:server` would import the package's `__init__.py` instead of the WSGI entry point. This is a production crash, not a subtle bug. Fix: rename entry point to `wsgi.py`. This exact issue was already documented in velocity-tool's FAILURES.md — the plan review's feasibility agent caught it before implementation.

**Callback timeouts from unoptimized scan data (found in browser QA).**
All 4 view modules loaded their own copy of ~2M weekly scan rows and processed them per callback invocation. On Fly.io (1024MB), callbacks timed out before completing, producing "server did not respond" errors. On the client side this looked like (a) design system not loading (page hung before CSS rendered) and (b) charts empty on filter selection. Root cause was pure performance — not a CSS or filter bug.

**pandas merge column collision (retailer_id).**
`door_count.py` merged AUTH (which has `retailer_id`) with STORE_INFO (also has `retailer_id`) on `store_id`. pandas silently renamed to `retailer_id_x` / `retailer_id_y`. The subsequent `groupby(["retailer_id", ...])` threw KeyError. Fix: only merge `retailer_name` from STORE_INFO since AUTH already has `retailer_id`. Lesson: when merging DataFrames that share column names beyond the join key, be explicit about which columns to pull.
