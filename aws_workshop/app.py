"""Return Radar - Flask application.

Serves the customer questionnaire and the seller dashboard, and exposes the
backend-driven adaptive question API.
"""
from flask import Flask, render_template, request, jsonify

import database
import questions

app = Flask(__name__)

# Initialize the database schema on startup.
database.init_db()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Customer-facing landing page + questionnaire shell."""
    return render_template("index.html", categories=questions.CATEGORIES)


@app.route("/dashboard")
def dashboard():
    """Seller-facing dashboard page."""
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/categories")
def categories():
    """Return the list of product categories."""
    return jsonify(questions.CATEGORIES)


@app.route("/next-question", methods=["POST"])
def next_question():
    """Given a category and the answers so far, return the next question.

    Request JSON: {"category": "<id>", "answers": {question_id: value, ...}}
    Response JSON: {"done": bool, "question": {...}?}
    """
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    answers = data.get("answers") or {}

    if not questions.is_valid_category(category):
        return jsonify({"error": "Invalid or missing category."}), 400
    if not isinstance(answers, dict):
        return jsonify({"error": "answers must be an object."}), 400

    result = questions.get_next_question(category, answers)
    return jsonify(result)


@app.route("/submit", methods=["POST"])
def submit():
    """Persist a completed questionnaire.

    Request JSON: {"category": "<id>", "answers": {question_id: value, ...}}
    Response JSON: {"ok": True, "submission_id": int}
    """
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    answers = data.get("answers") or {}

    if not questions.is_valid_category(category):
        return jsonify({"error": "Invalid or missing category."}), 400
    if not isinstance(answers, dict) or not answers:
        return jsonify({"error": "answers must be a non-empty object."}), 400

    # Guard: only accept submissions whose flow is actually complete.
    status = questions.get_next_question(category, answers)
    if not status.get("done"):
        return jsonify({"error": "Questionnaire is not complete."}), 400

    records = questions.build_answer_records(category, answers)
    final_reason = questions.summarize_reason(category, answers)
    submission_id = database.save_submission(
        category=questions.CATEGORY_NAMES[category],
        answers=records,
        final_reason=final_reason,
    )
    return jsonify({"ok": True, "submission_id": submission_id})


@app.route("/stats")
def stats():
    """Aggregated stats for the seller dashboard."""
    data = database.get_stats()
    data["submissions"] = database.get_all_submissions()
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
