"""Product catalog for Return Radar.

Each product belongs to one of the questionnaire categories and carries a
`units_sold` figure. Defect rate on the Issue Investigation page is computed as
returns-reporting-a-problem / units_sold, so this volume data is what makes the
percentage real rather than a share-of-returns.

This is demo seed data: realistic model names and plausible sales volumes so the
investigation page tells a believable story for judges.
"""

# category id (matches questions.CATEGORIES) -> list of product dicts.
PRODUCTS = [
    # Electronics -- includes the "headphones won't charge" style story.
    {"id": "soundmax-x200", "model": "SoundMax X200 Headphones", "category": "electronics", "units_sold": 4200},
    {"id": "soundmax-air", "model": "SoundMax Air Earbuds", "category": "electronics", "units_sold": 3100},
    {"id": "pixel-tab-10", "model": "PixelTab 10 Tablet", "category": "electronics", "units_sold": 1800},
    {"id": "chargefast-65w", "model": "ChargeFast 65W Adapter", "category": "electronics", "units_sold": 5600},

    # Clothing
    {"id": "aurora-jacket", "model": "Aurora Rain Jacket", "category": "clothing", "units_sold": 2200},
    {"id": "everyday-tee", "model": "Everyday Cotton Tee", "category": "clothing", "units_sold": 9800},
    {"id": "slimfit-jeans", "model": "SlimFit Stretch Jeans", "category": "clothing", "units_sold": 3400},

    # Home & Kitchen
    {"id": "brewpro-coffee", "model": "BrewPro Coffee Maker", "category": "home", "units_sold": 2700},
    {"id": "glasslock-set", "model": "GlassLock Container Set", "category": "home", "units_sold": 4100},

    # Beauty & Health
    {"id": "glow-serum", "model": "GlowDaily Vitamin C Serum", "category": "beauty", "units_sold": 6200},
    {"id": "silkmatte-foundation", "model": "SilkMatte Foundation", "category": "beauty", "units_sold": 3800},

    # Toys & Games
    {"id": "blockworld-500", "model": "BlockWorld 500pc Set", "category": "toys", "units_sold": 2900},
    {"id": "rc-speedster", "model": "RC Speedster Car", "category": "toys", "units_sold": 1600},

    # Footwear
    {"id": "trailblaze-runner", "model": "TrailBlaze Running Shoe", "category": "footwear", "units_sold": 5200},
    {"id": "comfywalk-loafer", "model": "ComfyWalk Loafer", "category": "footwear", "units_sold": 2400},

    # Books & Media
    {"id": "atlas-of-stars", "model": "Atlas of the Stars (Hardcover)", "category": "books", "units_sold": 1500},

    # Sporting Goods
    {"id": "proflex-yogamat", "model": "ProFlex Yoga Mat", "category": "sporting", "units_sold": 3300},
    {"id": "aero-tennis", "model": "Aero Tennis Racket", "category": "sporting", "units_sold": 1900},
]

PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}
PRODUCT_IDS = set(PRODUCTS_BY_ID)


def is_valid_product(product_id):
    return product_id in PRODUCT_IDS


def products_for_category(category_id):
    """Return the products belonging to a given category id."""
    return [p for p in PRODUCTS if p["category"] == category_id]


def model_name(product_id):
    p = PRODUCTS_BY_ID.get(product_id)
    return p["model"] if p else None


def units_sold(product_id):
    p = PRODUCTS_BY_ID.get(product_id)
    return p["units_sold"] if p else None


def category_of(product_id):
    p = PRODUCTS_BY_ID.get(product_id)
    return p["category"] if p else None
