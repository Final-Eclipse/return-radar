"""Seed the Return Radar database with sample submissions.

Run this before a demo so the seller dashboard shows realistic data:

    python seed.py

It walks the real adaptive engine for each sample so stored answers and
reasons match exactly what a customer would have produced.
"""
import random

import database
import questions


# (category_id, forced reason) pairs. The rest of each path picks the first
# option, which is enough to produce a complete, realistic submission.
SAMPLES = [
    ("clothing", "fit"),
    ("clothing", "fit"),
    ("clothing", "quality"),
    ("clothing", "appearance"),
    ("electronics", "defective"),
    ("electronics", "defective"),
    ("electronics", "compatibility"),
    ("electronics", "not_as_described"),
    ("home", "damaged"),
    ("home", "size"),
    ("beauty", "reaction"),
    ("beauty", "not_as_described"),
    ("toys", "safety"),
    ("toys", "defective"),
    ("footwear", "fit"),
    ("footwear", "fit"),
    ("footwear", "comfort"),
    ("books", "damaged"),
    ("sporting", "performance"),
    ("sporting", "size"),
]


def build_answers(category, reason):
    """Walk the engine to a complete answer set, forcing the given reason."""
    answers = {}
    for _ in range(12):  # safety bound
        result = questions.get_next_question(category, answers)
        if result["done"]:
            break
        q = result["question"]
        if q["id"] == "reason":
            answers[q["id"]] = reason
        else:
            # Mix it up a little so the dashboard isn't all identical.
            answers[q["id"]] = random.choice(q["options"])["value"]
    return answers


def main():
    database.init_db()
    created = 0
    for category, reason in SAMPLES:
        answers = build_answers(category, reason)
        records = questions.build_answer_records(category, answers)
        final_reason = questions.summarize_reason(category, answers)
        database.save_submission(
            category=questions.CATEGORY_NAMES[category],
            answers=records,
            final_reason=final_reason,
        )
        created += 1
    print(f"Seeded {created} sample submissions into {database.DB_PATH}")


if __name__ == "__main__":
    main()
