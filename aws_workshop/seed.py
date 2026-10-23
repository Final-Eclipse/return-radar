"""Seed the Return Radar database with sample submissions.

Run this before a demo so the seller dashboard and the Issue Investigation page
show realistic, story-worthy data:

    python seed.py

Each sample walks the real adaptive engine so stored answers and reasons match
exactly what a customer would have produced, and every sample is tagged with a
specific product so the investigation page can compute real defect rates.

The data is shaped to tell a clear story: the "SoundMax X200 Headphones"
product has an elevated rate of a specific charging/power problem, which stands
out against the rest of the Electronics category.
"""
import products as product_catalog
import database
import questions


# Each sample is a dict describing one return:
#   product : catalog product id
#   reason  : value for the top-level "reason" question (drives branching)
#   path    : optional dict of {question_id: value} to force specific deeper
#             answers so a specific problem clusters. Any unspecified question
#             falls back to the first option.
#   count   : how many identical submissions to create (default 1)
SAMPLES = [
    # --- The headline story: SoundMax X200 won't power on / charge ---
    {
        "product": "soundmax-x200",
        "reason": "defective",
        "path": {"defect_type": "wont_power", "defect_timing": "doa"},
        "count": 9,
    },
    {
        "product": "soundmax-x200",
        "reason": "defective",
        "path": {"defect_type": "intermittent", "defect_timing": "days"},
        "count": 3,
    },
    {
        "product": "soundmax-x200",
        "reason": "not_as_described",
        "path": {"described_detail": "specs"},
        "count": 2,
    },
    # --- A sibling for comparison: SoundMax Air, far fewer issues ---
    {
        "product": "soundmax-air",
        "reason": "defective",
        "path": {"defect_type": "missing_parts", "defect_timing": "doa"},
        "count": 2,
    },
    {
        "product": "soundmax-air",
        "reason": "compatibility",
        "path": {"compat_detail": "device"},
        "count": 1,
    },
    # --- Other electronics, to form a category baseline ---
    {
        "product": "pixel-tab-10",
        "reason": "defective",
        "path": {"defect_type": "physical", "defect_timing": "doa"},
        "count": 2,
    },
    {
        "product": "chargefast-65w",
        "reason": "compatibility",
        "path": {"compat_detail": "region"},
        "count": 2,
    },
    # --- Clothing ---
    {"product": "aurora-jacket", "reason": "fit", "path": {"fit_issue": "too_small"}, "count": 4},
    {"product": "everyday-tee", "reason": "quality", "path": {"quality_detail": "material"}, "count": 3},
    {"product": "slimfit-jeans", "reason": "appearance", "path": {"appearance_detail": "color"}, "count": 2},
    # --- Home & Kitchen ---
    {"product": "brewpro-coffee", "reason": "damaged", "path": {"damage_point": "shipping"}, "count": 3},
    {"product": "glasslock-set", "reason": "quality", "path": {"quality_detail": "flimsy"}, "count": 2},
    # --- Beauty & Health ---
    {"product": "glow-serum", "reason": "reaction", "path": {"reaction_detail": "irritation"}, "count": 3},
    {"product": "silkmatte-foundation", "reason": "not_as_described", "path": {"shade_detail": "lighter"}, "count": 2},
    # --- Toys & Games ---
    {"product": "blockworld-500", "reason": "missing", "count": 2},
    {"product": "rc-speedster", "reason": "defective", "path": {"defect_detail": "broke_fast"}, "count": 2},
    # --- Footwear ---
    {"product": "trailblaze-runner", "reason": "fit", "path": {"fit_detail": "too_small"}, "count": 5},
    {"product": "comfywalk-loafer", "reason": "comfort", "path": {"comfort_detail": "rubbing"}, "count": 2},
    # --- Books & Media ---
    {"product": "atlas-of-stars", "reason": "damaged", "path": {"damage_detail": "cover"}, "count": 2},
    # --- Sporting Goods ---
    {"product": "proflex-yogamat", "reason": "performance", "path": {"performance_detail": "durability"}, "count": 3},
    {"product": "aero-tennis", "reason": "size", "path": {"size_detail": "too_large"}, "count": 1},
]


def build_answers(category, reason, path):
    """Walk the engine to a complete answer set, using the forced path."""
    path = path or {}
    answers = {}
    for _ in range(12):  # safety bound
        result = questions.get_next_question(category, answers)
        if result["done"]:
            break
        q = result["question"]
        qid = q["id"]
        if qid == "reason":
            answers[qid] = reason
        elif qid in path:
            answers[qid] = path[qid]
        else:
            answers[qid] = q["options"][0]["value"]
    return answers


def main():
    database.init_db()
    created = 0
    for sample in SAMPLES:
        pid = sample["product"]
        category = product_catalog.category_of(pid)
        model = product_catalog.model_name(pid)
        if category is None:
            raise ValueError(f"Unknown product in seed: {pid}")

        for _ in range(sample.get("count", 1)):
            answers = build_answers(category, sample["reason"], sample.get("path"))
            records = questions.build_answer_records(category, answers)
            final_reason = questions.summarize_reason(category, answers)
            database.save_submission(
                category=questions.CATEGORY_NAMES[category],
                answers=records,
                final_reason=final_reason,
                product_id=pid,
                product_model=model,
            )
            created += 1

    print(f"Seeded {created} sample submissions into {database.DB_PATH}")


if __name__ == "__main__":
    main()
