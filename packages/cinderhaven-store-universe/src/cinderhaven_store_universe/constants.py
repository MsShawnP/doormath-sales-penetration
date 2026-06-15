"""Canonical IDs, SKU definitions, and shared constants for the Cinderhaven store universe."""

import pandas as pd

SEED = 42

DEMO_AS_OF_DATE = pd.Timestamp("2025-12-29")

RETAILERS = {
    "RET-WALMART": {"name": "Walmart", "door_count": 180},
    "RET-COSTCO": {"name": "Costco", "door_count": 60},
    "RET-WHOLEFOODS": {"name": "Whole Foods", "door_count": 120},
    "RET-SPROUTS": {"name": "Sprouts", "door_count": 90},
    "RET-KROGER": {"name": "Kroger", "door_count": 150},
    "RET-REGIONAL": {"name": "Regional Group", "door_count": 40},
}

PRODUCT_LINES = {
    "AS": {
        "name": "Artisan Sauces",
        "skus": [f"CHP-AS-{i:03d}" for i in range(1, 11)],
    },
    "PS": {
        "name": "Pantry Staples",
        "skus": [f"CHP-PS-{i:03d}" for i in range(1, 11)],
    },
    "SC": {
        "name": "Specialty Condiments",
        "skus": [f"CHP-SC-{i:03d}" for i in range(1, 11)],
    },
    "DG": {
        "name": "Dried Goods",
        "skus": [f"CHP-DG-{i:03d}" for i in range(1, 11)],
    },
    "SB": {
        "name": "Snack Bites",
        "skus": [f"CHP-SB-{i:03d}" for i in range(1, 11)],
    },
}

ALL_SKUS = []
for line_info in PRODUCT_LINES.values():
    ALL_SKUS.extend(line_info["skus"])

REGIONS = ["Northeast", "Southeast", "Midwest", "West"]

VOLUME_TIERS = ["A", "B", "C"]

# Volume tier distribution per retailer: (A%, B%, C%)
VOLUME_TIER_WEIGHTS = {
    "RET-WALMART": (0.60, 0.30, 0.10),
    "RET-COSTCO": (0.70, 0.20, 0.10),
    "RET-WHOLEFOODS": (0.40, 0.40, 0.20),
    "RET-SPROUTS": (0.35, 0.40, 0.25),
    "RET-KROGER": (0.40, 0.35, 0.25),
    "RET-REGIONAL": (0.15, 0.35, 0.50),
}

# Authorization rate by retailer and product line prefix
# Values are approximate target rates; actual generation uses these as probabilities
AUTH_RATES = {
    "RET-WHOLEFOODS": {"AS": 0.95, "PS": 0.70, "SC": 0.95, "DG": 0.70, "SB": 0.70},
    "RET-WALMART": {"AS": 0.55, "PS": 0.60, "SC": 0.50, "DG": 0.55, "SB": 0.55},
    "RET-COSTCO": {"AS": 0.45, "PS": 0.50, "SC": 0.40, "DG": 0.45, "SB": 0.45},
    "RET-KROGER": {"AS": 0.80, "PS": 0.85, "SC": 0.75, "DG": 0.80, "SB": 0.80},
    "RET-SPROUTS": {"AS": 0.80, "PS": 0.55, "SC": 0.80, "DG": 0.80, "SB": 0.55},
    "RET-REGIONAL": {"AS": 0.50, "PS": 0.55, "SC": 0.45, "DG": 0.50, "SB": 0.50},
}

# Scan probability by volume tier
SCAN_RATES = {
    "A": 0.90,
    "B": 0.80,
    "C": 0.70,
}
