# lailara-palette

Color and typography constants from the Lailara Design System v2, as importable
Python values. Vendored into each Cinderhaven tool so every deliverable draws
its colors from one source rather than restating hex literals.

## Install

```
pip install -e packages/lailara-palette
```

Not published to a package index — install by path.

## Usage

```python
from lailara_palette import LL_CANVAS, LL_INK, LL_SEQ

LL_CANVAS  # '#f5f3ee' — the warm off-white page background
LL_INK     # '#0d0d0d' — London-5, chart titles and primary headings
LL_SEQ     # the teal sequential ramp
```

Consumers re-export these under short semantic aliases rather than importing
them at every call site. See `app/constants.py` in the Door Math tool for the
pattern.

## Stack

Python 3.9+. No runtime dependencies.

## Notes

Every value traces back to a named family and lightness step in
`LAILARA_DESIGN_SYSTEM.md`. Do not add ad-hoc hex values here — add the token to
the design system first, then mirror it.

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics
consulting for specialty food brands scaling into national retail.
