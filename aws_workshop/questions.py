"""Adaptive question engine for Return Radar.

The question flow is backend-driven: the frontend sends the chosen category and
the answers collected so far, and `get_next_question` walks a per-category
question tree to decide what to ask next (or signals completion).

Tree model
----------
Each category maps to an ordered list of question nodes. A node is asked only if
its `show_if` predicate matches the answers gathered so far. This keeps the data
declarative while supporting 3-4 level deep branching that depends on earlier
answers. The first node whose `show_if` passes and that has not yet been
answered becomes the next question. When no such node remains, the flow is
complete.
"""

# Product categories (order drives the landing-page grid).
CATEGORIES = [
    {"id": "clothing", "name": "Clothing & Apparel", "icon": "\U0001F455"},
    {"id": "electronics", "name": "Electronics", "icon": "\U0001F50C"},
    {"id": "home", "name": "Home & Kitchen", "icon": "\U0001F3E0"},
    {"id": "beauty", "name": "Beauty & Health", "icon": "\U0001F9F4"},
    {"id": "toys", "name": "Toys & Games", "icon": "\U0001F9F8"},
    {"id": "footwear", "name": "Footwear", "icon": "\U0001F45F"},
    {"id": "books", "name": "Books & Media", "icon": "\U0001F4DA"},
    {"id": "sporting", "name": "Sporting Goods", "icon": "\U000026BD"},
]

CATEGORY_IDS = {c["id"] for c in CATEGORIES}
CATEGORY_NAMES = {c["id"]: c["name"] for c in CATEGORIES}


def _opt(value, label):
    """Helper to build a question option."""
    return {"value": value, "label": label}


# Shared opening question used by every category: the top-level reason.
# Branching below keys off the answer to "reason".
def _reason_question(options):
    return {
        "id": "reason",
        "text": "What is the main reason you're returning this item?",
        "help": "Pick the option that best matches your situation.",
        "options": options,
    }


# Each entry is (node, show_if). show_if receives the answers dict
# (question_id -> answer_value) and returns True when the node applies.
QUESTION_TREE = {
    "clothing": [
        (
            _reason_question([
                _opt("fit", "It didn't fit"),
                _opt("quality", "Quality wasn't as expected"),
                _opt("appearance", "Looked different from photos"),
                _opt("wrong_item", "Received the wrong item"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "fit_issue",
                "text": "How was the fit off?",
                "options": [
                    _opt("too_small", "Too small"),
                    _opt("too_large", "Too large"),
                    _opt("wrong_shape", "Wrong shape / cut"),
                ],
            },
            lambda a: a.get("reason") == "fit",
        ),
        (
            {
                "id": "size_vs_chart",
                "text": "Did the size match the size chart on the listing?",
                "options": [
                    _opt("matched", "Yes, it matched the chart"),
                    _opt("no_chart", "There was no size chart"),
                    _opt("mismatch", "No, it differed from the chart"),
                ],
            },
            lambda a: a.get("reason") == "fit",
        ),
        (
            {
                "id": "quality_detail",
                "text": "What quality problem did you notice?",
                "options": [
                    _opt("material", "Material felt cheap"),
                    _opt("stitching", "Poor stitching / seams"),
                    _opt("damaged", "Arrived damaged"),
                ],
            },
            lambda a: a.get("reason") == "quality",
        ),
        (
            {
                "id": "appearance_detail",
                "text": "What looked different from the photos?",
                "options": [
                    _opt("color", "The color"),
                    _opt("pattern", "The pattern / print"),
                    _opt("style", "The overall style"),
                ],
            },
            lambda a: a.get("reason") == "appearance",
        ),
    ],
    "electronics": [
        (
            _reason_question([
                _opt("defective", "Item is defective / not working"),
                _opt("not_as_described", "Not as described"),
                _opt("compatibility", "Compatibility issue"),
                _opt("wrong_item", "Received the wrong item"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "defect_type",
                "text": "What kind of defect are you experiencing?",
                "options": [
                    _opt("wont_power", "Won't power on"),
                    _opt("intermittent", "Works intermittently"),
                    _opt("physical", "Physical damage out of the box"),
                    _opt("missing_parts", "Missing parts / accessories"),
                ],
            },
            lambda a: a.get("reason") == "defective",
        ),
        (
            {
                "id": "defect_timing",
                "text": "When did the problem start?",
                "options": [
                    _opt("doa", "Dead on arrival"),
                    _opt("days", "Within a few days"),
                    _opt("weeks", "After a couple of weeks"),
                ],
            },
            lambda a: a.get("reason") == "defective",
        ),
        (
            {
                "id": "compat_detail",
                "text": "What wasn't compatible?",
                "options": [
                    _opt("device", "My device / model"),
                    _opt("software", "Software / OS version"),
                    _opt("region", "Region / plug / voltage"),
                ],
            },
            lambda a: a.get("reason") == "compatibility",
        ),
        (
            {
                "id": "described_detail",
                "text": "Which detail didn't match the listing?",
                "options": [
                    _opt("specs", "Technical specs"),
                    _opt("capacity", "Storage / capacity"),
                    _opt("condition", "Condition (new vs used)"),
                ],
            },
            lambda a: a.get("reason") == "not_as_described",
        ),
    ],
    "home": [
        (
            _reason_question([
                _opt("damaged", "Arrived damaged / broken"),
                _opt("size", "Wrong size for my space"),
                _opt("quality", "Quality below expectations"),
                _opt("missing", "Missing parts"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "damage_point",
                "text": "When do you think the damage happened?",
                "options": [
                    _opt("shipping", "During shipping"),
                    _opt("manufacture", "Manufacturing defect"),
                    _opt("packaging", "Poor packaging"),
                ],
            },
            lambda a: a.get("reason") == "damaged",
        ),
        (
            {
                "id": "size_detail",
                "text": "How was the size wrong?",
                "options": [
                    _opt("too_big", "Too big"),
                    _opt("too_small", "Too small"),
                    _opt("dims_unclear", "Dimensions were unclear in listing"),
                ],
            },
            lambda a: a.get("reason") == "size",
        ),
        (
            {
                "id": "quality_detail",
                "text": "What about the quality disappointed you?",
                "options": [
                    _opt("flimsy", "Felt flimsy / cheap"),
                    _opt("finish", "Poor finish"),
                    _opt("function", "Didn't work as intended"),
                ],
            },
            lambda a: a.get("reason") == "quality",
        ),
    ],
    "beauty": [
        (
            _reason_question([
                _opt("reaction", "Caused a skin reaction"),
                _opt("not_as_described", "Color / shade not as described"),
                _opt("expired", "Product seemed expired / old"),
                _opt("packaging", "Packaging damaged / leaking"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "reaction_detail",
                "text": "What kind of reaction did you have?",
                "options": [
                    _opt("irritation", "Irritation / redness"),
                    _opt("breakout", "Breakout"),
                    _opt("allergy", "Allergic reaction"),
                ],
            },
            lambda a: a.get("reason") == "reaction",
        ),
        (
            {
                "id": "reaction_patch",
                "text": "Did you do a patch test first?",
                "options": [
                    _opt("yes", "Yes"),
                    _opt("no", "No"),
                ],
            },
            lambda a: a.get("reason") == "reaction",
        ),
        (
            {
                "id": "shade_detail",
                "text": "How did the shade differ?",
                "options": [
                    _opt("lighter", "Lighter than shown"),
                    _opt("darker", "Darker than shown"),
                    _opt("undertone", "Wrong undertone"),
                ],
            },
            lambda a: a.get("reason") == "not_as_described",
        ),
    ],
    "toys": [
        (
            _reason_question([
                _opt("defective", "Broken / defective"),
                _opt("age", "Not suitable for the age"),
                _opt("missing", "Missing pieces"),
                _opt("safety", "Safety concern"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "safety_detail",
                "text": "What was the safety concern?",
                "options": [
                    _opt("small_parts", "Small parts / choking hazard"),
                    _opt("sharp", "Sharp edges"),
                    _opt("materials", "Material / smell concern"),
                ],
            },
            lambda a: a.get("reason") == "safety",
        ),
        (
            {
                "id": "age_detail",
                "text": "How was the age fit off?",
                "options": [
                    _opt("too_advanced", "Too advanced for the child"),
                    _opt("too_simple", "Too simple / boring"),
                    _opt("label_wrong", "Age label was misleading"),
                ],
            },
            lambda a: a.get("reason") == "age",
        ),
        (
            {
                "id": "defect_detail",
                "text": "What was broken or defective?",
                "options": [
                    _opt("doa", "Didn't work out of the box"),
                    _opt("broke_fast", "Broke very quickly"),
                    _opt("parts", "A specific part failed"),
                ],
            },
            lambda a: a.get("reason") == "defective",
        ),
    ],
    "footwear": [
        (
            _reason_question([
                _opt("fit", "Didn't fit"),
                _opt("comfort", "Uncomfortable"),
                _opt("quality", "Quality / durability issue"),
                _opt("appearance", "Looked different from photos"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "fit_detail",
                "text": "How did they fit?",
                "options": [
                    _opt("too_small", "Too small / tight"),
                    _opt("too_large", "Too large / loose"),
                    _opt("width", "Width was off"),
                ],
            },
            lambda a: a.get("reason") == "fit",
        ),
        (
            {
                "id": "fit_size_ref",
                "text": "Did you order your usual size?",
                "options": [
                    _opt("usual", "Yes, my usual size"),
                    _opt("sized_up", "I sized up"),
                    _opt("sized_down", "I sized down"),
                ],
            },
            lambda a: a.get("reason") == "fit",
        ),
        (
            {
                "id": "comfort_detail",
                "text": "What made them uncomfortable?",
                "options": [
                    _opt("arch", "Arch support"),
                    _opt("stiff", "Too stiff"),
                    _opt("rubbing", "Rubbing / blisters"),
                ],
            },
            lambda a: a.get("reason") == "comfort",
        ),
    ],
    "books": [
        (
            _reason_question([
                _opt("damaged", "Arrived damaged"),
                _opt("wrong_item", "Wrong edition / item"),
                _opt("quality", "Print / media quality issue"),
                _opt("duplicate", "Already owned it / duplicate"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "damage_detail",
                "text": "What was the damage?",
                "options": [
                    _opt("cover", "Bent / torn cover"),
                    _opt("pages", "Damaged pages"),
                    _opt("disc", "Scratched disc / media"),
                ],
            },
            lambda a: a.get("reason") == "damaged",
        ),
        (
            {
                "id": "edition_detail",
                "text": "What was wrong with the edition?",
                "options": [
                    _opt("format", "Wrong format (e.g. paperback vs hardcover)"),
                    _opt("language", "Wrong language"),
                    _opt("version", "Older / different version"),
                ],
            },
            lambda a: a.get("reason") == "wrong_item",
        ),
    ],
    "sporting": [
        (
            _reason_question([
                _opt("size", "Wrong size"),
                _opt("defective", "Defective / damaged"),
                _opt("performance", "Didn't perform as expected"),
                _opt("compatibility", "Compatibility / fit with gear"),
                _opt("changed_mind", "Changed my mind"),
            ]),
            lambda a: True,
        ),
        (
            {
                "id": "performance_detail",
                "text": "How did performance fall short?",
                "options": [
                    _opt("durability", "Not durable enough"),
                    _opt("comfort", "Uncomfortable in use"),
                    _opt("effectiveness", "Didn't help my activity"),
                ],
            },
            lambda a: a.get("reason") == "performance",
        ),
        (
            {
                "id": "size_detail",
                "text": "How was the size off?",
                "options": [
                    _opt("too_small", "Too small"),
                    _opt("too_large", "Too large"),
                    _opt("sizing_unclear", "Sizing info was unclear"),
                ],
            },
            lambda a: a.get("reason") == "size",
        ),
        (
            {
                "id": "compat_detail",
                "text": "What didn't it fit or work with?",
                "options": [
                    _opt("existing_gear", "My existing gear"),
                    _opt("body", "My body / frame"),
                    _opt("accessories", "Required accessories"),
                ],
            },
            lambda a: a.get("reason") == "compatibility",
        ),
    ],
}


# A final, shared confidence question asked once the category-specific branch is
# exhausted. It applies to every path, giving a consistent closing question.
FINAL_QUESTION = {
    "id": "recommend",
    "text": "Based on this experience, how likely are you to buy from this seller again?",
    "options": [
        _opt("very_likely", "Very likely"),
        _opt("maybe", "Maybe"),
        _opt("unlikely", "Unlikely"),
    ],
}


def is_valid_category(category):
    return category in CATEGORY_IDS


def get_next_question(category, answers):
    """Return the next question for this category given answers so far.

    Args:
        category: category id.
        answers: dict mapping question_id -> answer_value.

    Returns:
        A dict:
          {"done": False, "question": {...}}  when there is a question to ask, or
          {"done": True}                      when the flow is complete.
    """
    if not is_valid_category(category):
        raise ValueError(f"Unknown category: {category!r}")

    answers = answers or {}
    nodes = QUESTION_TREE[category]

    for node, show_if in nodes:
        if show_if(answers) and node["id"] not in answers:
            return {"done": False, "question": node}

    # Category branch exhausted; ask the shared closing question once.
    if FINAL_QUESTION["id"] not in answers:
        return {"done": False, "question": FINAL_QUESTION}

    return {"done": True}


def _label_for(question, value):
    """Human-readable label for a stored answer value."""
    for opt in question.get("options", []):
        if opt["value"] == value:
            return opt["label"]
    return value


def build_answer_records(category, answers):
    """Convert a raw answers dict into ordered records for persistence.

    Walks the same tree logic so stored question text and labels line up with
    what the customer actually saw.
    """
    if not is_valid_category(category):
        raise ValueError(f"Unknown category: {category!r}")

    records = []
    nodes = QUESTION_TREE[category]
    for node, show_if in nodes:
        qid = node["id"]
        if show_if(answers) and qid in answers:
            records.append(
                {
                    "question_id": qid,
                    "question_text": node["text"],
                    "answer_value": _label_for(node, answers[qid]),
                }
            )
    if FINAL_QUESTION["id"] in answers:
        records.append(
            {
                "question_id": FINAL_QUESTION["id"],
                "question_text": FINAL_QUESTION["text"],
                "answer_value": _label_for(FINAL_QUESTION, answers[FINAL_QUESTION["id"]]),
            }
        )
    return records


def summarize_reason(category, answers):
    """Produce a short primary-reason label for dashboard aggregation."""
    reason = answers.get("reason")
    if reason is None:
        return None
    # The reason question is always the first node in each category.
    reason_node = QUESTION_TREE[category][0][0]
    return _label_for(reason_node, reason)
