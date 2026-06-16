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

SKU_NAMES = {
    "CHP-AS-001": "Roasted Garlic Marinara",
    "CHP-AS-002": "Smoky Chipotle BBQ",
    "CHP-AS-003": "Thai Basil Coconut",
    "CHP-AS-004": "Lemon Herb Pesto",
    "CHP-AS-005": "Spicy Arrabbiata",
    "CHP-AS-006": "Wild Mushroom Ragù",
    "CHP-AS-007": "Mango Habanero",
    "CHP-AS-008": "Sun-Dried Tomato Cream",
    "CHP-AS-009": "Balsamic Fig Glaze",
    "CHP-AS-010": "Green Chile Verde",
    "CHP-PS-001": "Stone-Ground Mustard",
    "CHP-PS-002": "Organic Tahini",
    "CHP-PS-003": "Smoked Paprika Oil",
    "CHP-PS-004": "Truffle Honey",
    "CHP-PS-005": "Everything Bagel Seasoning",
    "CHP-PS-006": "Calabrian Chili Spread",
    "CHP-PS-007": "Toasted Sesame Vinaigrette",
    "CHP-PS-008": "Herbed Garlic Butter",
    "CHP-PS-009": "Preserved Lemon Paste",
    "CHP-PS-010": "Black Garlic Aioli",
    "CHP-SC-001": "Bourbon Bacon Jam",
    "CHP-SC-002": "Jalapeño Peach Relish",
    "CHP-SC-003": "Wasabi Ginger Mayo",
    "CHP-SC-004": "Chimichurri Verde",
    "CHP-SC-005": "Harissa Yogurt Sauce",
    "CHP-SC-006": "Pickled Red Onion",
    "CHP-SC-007": "Tamarind Date Chutney",
    "CHP-SC-008": "Roasted Pepper Romesco",
    "CHP-SC-009": "Miso Caramel Drizzle",
    "CHP-SC-010": "Chipotle Lime Mayo",
    "CHP-DG-001": "Heritage Grain Blend",
    "CHP-DG-002": "Smoked Almond Granola",
    "CHP-DG-003": "Spiced Lentil Soup Mix",
    "CHP-DG-004": "Wild Rice Pilaf Kit",
    "CHP-DG-005": "Turmeric Quinoa Bowl",
    "CHP-DG-006": "Maple Pecan Oatmeal",
    "CHP-DG-007": "Moroccan Couscous",
    "CHP-DG-008": "Black Bean Taco Kit",
    "CHP-DG-009": "Italian Wedding Soup Mix",
    "CHP-DG-010": "Thai Coconut Rice",
    "CHP-SB-001": "Rosemary Sea Salt Crisps",
    "CHP-SB-002": "Dark Chocolate Quinoa Bark",
    "CHP-SB-003": "Spicy Sriracha Cashews",
    "CHP-SB-004": "Olive Tapenade Crackers",
    "CHP-SB-005": "Cinnamon Maple Pecans",
    "CHP-SB-006": "Za'atar Pita Chips",
    "CHP-SB-007": "Teriyaki Seaweed Snaps",
    "CHP-SB-008": "Lemon Pepper Almonds",
    "CHP-SB-009": "Truffle Parmesan Popcorn",
    "CHP-SB-010": "Honey Chili Pistachios",
}

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

# Never-scan base rate by retailer — fraction of authorized pairs that are
# authorized on paper but never actually carried at the store level.
# Combined with per-SKU velocity modulation in scans.py.
NEVER_SCAN_RATES = {
    "RET-WHOLEFOODS": 0.03,
    "RET-COSTCO": 0.05,
    "RET-KROGER": 0.07,
    "RET-SPROUTS": 0.07,
    "RET-WALMART": 0.09,
    "RET-REGIONAL": 0.15,
}

# SKUs with delayed market entry — no scans before this ISO week
LATE_LAUNCH = {
    "CHP-AS-009": "2024-W27",
    "CHP-SB-006": "2024-W40",
}
