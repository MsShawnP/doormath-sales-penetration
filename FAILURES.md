# Door Math — Failures

## 2026-07-29

**A measurement tool read as evidence before checking it measured anything — twice.**
First: a font-weight probe requested `font-family: 'Source Sans 3', sans-serif` and
reported six weights collapsing into two groups, which looked like clean confirmation
of the CSS Fonts L4 nearest-match rule. It was measuring **Arial** throughout. The tell
was a "system fallback" control arm matching weight 400 to two decimal places — a
coincidence that isn't one. Second, minutes later: a ground-truth probe compared two
repos' stylesheets and reported identical widths, appearing to contradict the detector.
Same root cause — asking for the family *by name* lets any system-installed copy answer.
Fix both times: load each file under a **unique** family name nothing on the machine can
satisfy, and include a deliberately-broken path as a negative control. Lesson: a probe
needs an arm that fails when the probe is broken, or a null result is indistinguishable
from a clean one.

**A font-face detector that was syntactically right and semantically blind.**
Written to assert every `@font-face`'s declared weight matches its file's
`usWeightClass`. Two bugs, both found by running it against repos whose answers were
already known. (1) It resolved `url()` against the stylesheet's own directory, so the
PDF template's `fonts/…` — which WeasyPrint resolves against a passed `base_url` —
reported 8 false mismatches on a verified-clean repo. Fixed with a basename fallback
across the repo. (2) It didn't exclude `renv/`, returning 931 phantom mismatches from
vendored R package CSS. Lesson: the same error class recurred four times this project —
matching on filename instead of font family, a URL grep reading prose as a deploy claim,
config assumed at depth 1. Each rule was correct as written and wrong about what it
meant.

**"One canonical bad file propagated everywhere" was false.**
An early scan found 44 byte-identical copies of the bad latin file and 37 of latin-ext,
which suggested a known-bad hash list would find every instance. At least three variants
exist — `fe93b8f82d…`, `30164609c163` (28,740 bytes), and `c6ba61588d7d` (60,088 bytes,
nearly four times the correct file, still ExtraLight). The third sits in `lailara-frame`,
the first repo any sweep touches, and a hash list built from the first two walks straight
past it. Lesson: detect by the **defect** (`usWeightClass` ≠ declared weight), verify by
the **target** hash. Broad detector, exact verifier — never the reverse.

**WSL could not host WeasyPrint; Docker Desktop was the only route.**
Pango and Cairo were already present in WSL Ubuntu, so a venv looked like the cheap path
to rendering the PDF on Linux. `ensurepip` is unavailable (Ubuntu splits `python3-venv`),
and there was no `pip`, `uv`, `pipx`, or passwordless sudo. Every remaining option meant
downloading and executing an installer. Launching the already-installed Docker Desktop
was both permitted and better — the Dockerfile *is* production, so the render tested what
actually ships, including proving the brand fonts win over the `fonts-liberation` package
the image installs.

**Repo-wide scans under-counted three times before settling.**
28 repos, then 34, then a correction to the deploy-config figures. The affected-repo count
was wrong because the glob matched filenames rather than the font's internal family name,
missing six repos — three of them linked from the portfolio. The deploy-config count was
wrong because it stat'd repo root, and seven of eight "no-deploy-config" repos keep
`wrangler.jsonc` or `fly.toml` one level down. Lesson: for a sweep, publish the discovery
*rule*, not a list of repo names. A list inherits every scan bug silently.

## 2026-07-27

**Chart labels were "fixed" against the wrong overlap and shipped wrong numbers
for six weeks.** Session 11 addressed gap-label collisions with
`textposition="outside"` and `cliponaxis=False`. That stops Plotly clipping a
label at the axis — it does nothing about the label being painted over by the
bar. The outside label's text box starts ~13px left of the bar end, so the two
leading spaces used as padding were not enough and the first digit landed on the
navy segment. On the live site, Sprouts' 574 read as 674, Costco's 95 as 05, and
Regional Group's 315 as 815. Meanwhile every inside label overhung its own bar by
1–3px, clipping the last digit of 4,997 and 3,920. Lesson: a label-collision fix
has to be verified by measuring rendered geometry, not by looking at the chart —
the failure mode is a plausible-looking digit, not a visibly broken layout.

**Plotly reported the right font and rendered the wrong one.** Every sans
element in every chart — bar labels, axis ticks, legend, annotations, 74 painted
elements — rendered in Open Sans while `layout.font.family` and
`trace.textfont.family` both correctly held the Source Sans 3 stack and Plotly's
`_fullLayout` confirmed it had accepted them. Plotly injects a stylesheet setting
its container to Open Sans and only writes `font-family` onto text where it
differs from what it assumes the container carries. Chart titles escaped because
the serif family does get written inline, which made the whole thing look
correct at a glance. Lesson: for Plotly, verify the computed style of rendered
text; the Python-side figure spec can be right while the output is not.

**A test named for the project's hardest rule tested none of the project's
code.** `test_calculations_use_demo_as_of_date` asserted a constant inside the
data package and imported nothing from `app/`. Adding `datetime.now()` anywhere
in the app would have left it green while every silence figure shifted by ~30
weeks. Replaced with a source scan plus an exact-value assertion.

**Two tests went silent on exactly the regression they guarded.**
`test_correct_columns` wrapped its only assertion in `if rows:`, and
`test_all_exceptions_exceed_threshold` looped over the same list — so an empty
exceptions result turned both into no-ops and shipped an empty grid and empty CSV
with a green suite. Lesson: any test that iterates or conditions on a collection
needs a prior assertion that the collection is non-empty.

**Batch calculations had no parity guard, and the gap was invisible until
proved.** The Trends and Scorecard tabs run on `batch_*` reimplementations of
`calc_acv_pct` and `calc_tdp`, whose originals have no callers left in the app.
Injecting the exact suspected regression — batch ACV correct in the first quarter,
zero after — showed the pre-existing suite passing 130 tests completely blind to
it. Lesson: when a fast path duplicates a reference implementation, assert they
agree; and when claiming a coverage gap, inject the fault and watch the suite
stay green rather than reasoning about it.

**A fresh clone could never install.** `lailara-palette` is declared as a plain
dependency name and does not exist on any index; the README installed only the
other vendored package. pip treats an already-installed editable package as
satisfying a requirement, which is why the store universe worked and this did
not. Docker masked it entirely by installing both from local paths first. Lesson:
a Dockerfile that works is not evidence that the documented developer setup does
— test the README's own steps in a clean venv.

**The docs and the code disagreed about a colour, in both directions.**
DECISIONS.md and FAILURES.md both recorded the gap bar as London-70 grey chosen
for colour-vision safety; the shipped code uses Chicago navy. Either a future
session "restores" grey and silently reverts a deliberate change, or it burns
time re-deriving why the chart does not match the docs. Corrected in both files.

## 2026-07-02

**Tokyo-70 gap bar failed accessibility under red/green CVD.**
Used Tokyo-70 (#e68a9a, rose/berry) for the authorization-vs-scanning gap bar, paired with HK-35 (teal) for the scanning segment. Looked great under normal vision — two distinct hues for two semantically different segments. But teal and rose collapse to the same muddy olive under deuteranopia/protanopia, making the gap invisible. Reverted to a neutral grey, which is universally distinguishable. Lesson: when two bar segments sit side by side, check the pair under simulated CVD before committing, not just individually. (Superseded: the shipped colour is now Chicago navy `#1f2e7a`, which is CVD-safe against HK-35 teal by hue. See the 2026-07-27 correction.)

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
