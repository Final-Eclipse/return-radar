"""Return Radar - Flask application.

Serves the customer questionnaire and the seller-only dashboard / issue
investigation pages, and exposes the backend-driven adaptive question API.

Seller pages are protected by a simple session-based login. This is demo-grade
access control (a single shared seller password), not production auth, but it
genuinely gates the seller-only pages so customers cannot reach them.
"""
import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)

import database
import questions
import products as product_catalog

app = Flask(__name__)
# Secret key for signing the session cookie. Override via env var in real use.
app.secret_key = os.environ.get("RETURN_RADAR_SECRET", "dev-secret-change-me")

# Demo seller password. Override via env var for anything beyond a local demo.
SELLER_PASSWORD = os.environ.get("RETURN_RADAR_SELLER_PASSWORD", "seller123")

# Initialize the database schema on startup.
database.init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def seller_required(view):
    """Decorator that redirects to login for page views, 401s for JSON APIs."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_seller"):
            # API routes (expecting JSON) get a 401; pages get a redirect.
            if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
                return jsonify({"error": "Seller login required."}), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Customer-facing landing page + questionnaire shell."""
    return render_template("index.html", categories=questions.CATEGORIES)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Seller login. Grants a session flag on the correct password."""
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == SELLER_PASSWORD:
            session["is_seller"] = True
            dest = request.args.get("next") or url_for("dashboard")
            # Only allow local redirects.
            if not dest.startswith("/"):
                dest = url_for("dashboard")
            return redirect(dest)
        error = "Incorrect password. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("is_seller", None)
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Seller-only pages
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@seller_required
def dashboard():
    """Seller-facing dashboard page."""
    return render_template("dashboard.html")


@app.route("/investigation")
@seller_required
def investigation():
    """Seller-only Issue Investigation page."""
    return render_template("investigation.html")


# ---------------------------------------------------------------------------
# Public API (customer questionnaire)
# ---------------------------------------------------------------------------
@app.route("/categories")
def categories():
    """Return the list of product categories."""
    return jsonify(questions.CATEGORIES)


@app.route("/products")
def products_for_category():
    """Return the products in a given category: /products?category=<id>."""
    category = request.args.get("category")
    if not questions.is_valid_category(category):
        return jsonify({"error": "Invalid or missing category."}), 400
    return jsonify(product_catalog.products_for_category(category))


@app.route("/next-question", methods=["POST"])
def next_question():
    """Given a category and the answers so far, return the next question.

    Request JSON: {"category": "<id>", "answers": {question_id: value, ...}}
    Response JSON: {"done": bool, "question": {...}?, "progress": {...}}
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

    Request JSON:
        {"category": "<id>", "product_id": "<id>?",
         "answers": {question_id: value, ...}}
    Response JSON: {"ok": True, "submission_id": int}
    """
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    product_id = data.get("product_id")
    answers = data.get("answers") or {}

    if not questions.is_valid_category(category):
        return jsonify({"error": "Invalid or missing category."}), 400
    if not isinstance(answers, dict) or not answers:
        return jsonify({"error": "answers must be a non-empty object."}), 400

    # Validate the product if supplied, and ensure it matches the category.
    product_model = None
    if product_id:
        if not product_catalog.is_valid_product(product_id):
            return jsonify({"error": "Invalid product."}), 400
        if product_catalog.category_of(product_id) != category:
            return jsonify({"error": "Product does not match category."}), 400
        product_model = product_catalog.model_name(product_id)

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
        product_id=product_id,
        product_model=product_model,
    )
    return jsonify({"ok": True, "submission_id": submission_id})


# ---------------------------------------------------------------------------
# Seller-only API
# ---------------------------------------------------------------------------
@app.route("/stats")
@seller_required
def stats():
    """Aggregated stats for the seller dashboard."""
    data = database.get_stats()
    data["submissions"] = database.get_all_submissions()
    return jsonify(data)


@app.route("/investigation-data")
@seller_required
def investigation_data():
    """Issue Investigation aggregation for the seller-only page."""
    return jsonify(database.get_investigation())


if __name__ == "__main__":
    app.run(debug=True, port=5000)
