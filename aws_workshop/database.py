"""SQLite data layer for Return Radar.

Stores return-feedback submissions and their individual answers, each tagged
with the product category (and, where known, the specific product model) so
sellers can analyze why products come back.
"""
import sqlite3
import os
from datetime import datetime, timezone

import products as product_catalog
import questions as question_catalog

# Keep the DB file alongside this module inside the workspace.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "return_radar.db")


def get_connection(db_path=None):
    """Return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints (off by default in SQLite).
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Create tables if they do not already exist. Safe to call on startup."""
    conn = get_connection(db_path)
    try:
        # Create tables first (without indexes that depend on newer columns).
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                category      TEXT NOT NULL,
                created_at    TEXT NOT NULL,
                final_reason  TEXT,
                product_id    TEXT,
                product_model TEXT
            );

            CREATE TABLE IF NOT EXISTS answers (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                question_id   TEXT NOT NULL,
                question_text TEXT NOT NULL,
                answer_value  TEXT NOT NULL,
                FOREIGN KEY (submission_id) REFERENCES submissions(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS products (
                id         TEXT PRIMARY KEY,
                model      TEXT NOT NULL,
                category   TEXT NOT NULL,
                units_sold INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.commit()

        # Migrate older databases that predate the product columns. This must
        # run before creating any index that references those columns.
        _ensure_columns(conn)
        conn.commit()

        # Now safe to create indexes that reference the (possibly just-added)
        # product columns.
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_submissions_category
                ON submissions(category);
            CREATE INDEX IF NOT EXISTS idx_submissions_product
                ON submissions(product_id);
            """
        )

        # Keep the products table in sync with the catalog.
        _sync_products(conn)
        conn.commit()
    finally:
        conn.close()


def _ensure_columns(conn):
    """Add product columns to an existing submissions table if missing."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(submissions)")}
    if "product_id" not in existing:
        conn.execute("ALTER TABLE submissions ADD COLUMN product_id TEXT")
    if "product_model" not in existing:
        conn.execute("ALTER TABLE submissions ADD COLUMN product_model TEXT")


def _sync_products(conn):
    """Upsert the product catalog (model + category + units_sold) into the DB."""
    for p in product_catalog.PRODUCTS:
        conn.execute(
            """INSERT INTO products (id, model, category, units_sold)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   model = excluded.model,
                   category = excluded.category,
                   units_sold = excluded.units_sold""",
            (p["id"], p["model"], p["category"], p["units_sold"]),
        )


def save_submission(
    category,
    answers,
    final_reason=None,
    product_id=None,
    product_model=None,
    db_path=None,
):
    """Persist a completed submission plus its answers.

    Args:
        category: product category string.
        answers: list of dicts with keys question_id, question_text, answer_value.
        final_reason: short summary of the primary return reason (optional).
        product_id: catalog id of the specific product (optional).
        product_model: human-readable model name of the product (optional).

    Returns:
        The new submission id.
    """
    conn = get_connection(db_path)
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """INSERT INTO submissions
               (category, created_at, final_reason, product_id, product_model)
               VALUES (?, ?, ?, ?, ?)""",
            (category, created_at, final_reason, product_id, product_model),
        )
        submission_id = cur.lastrowid
        for a in answers:
            conn.execute(
                """INSERT INTO answers
                   (submission_id, question_id, question_text, answer_value)
                   VALUES (?, ?, ?, ?)""",
                (
                    submission_id,
                    a.get("question_id", ""),
                    a.get("question_text", ""),
                    a.get("answer_value", ""),
                ),
            )
        conn.commit()
        return submission_id
    finally:
        conn.close()


def get_submission(submission_id, db_path=None):
    """Return a single submission with its answers, or None if not found."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM submissions WHERE id = ?", (submission_id,)
        ).fetchone()
        if row is None:
            return None
        answers = conn.execute(
            "SELECT question_id, question_text, answer_value FROM answers "
            "WHERE submission_id = ? ORDER BY id",
            (submission_id,),
        ).fetchall()
        result = dict(row)
        result["answers"] = [dict(a) for a in answers]
        return result
    finally:
        conn.close()


def get_all_submissions(db_path=None):
    """Return all submissions (newest first) with their answers."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC, id DESC"
        ).fetchall()
        submissions = []
        for row in rows:
            answers = conn.execute(
                "SELECT question_id, question_text, answer_value FROM answers "
                "WHERE submission_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
            item = dict(row)
            item["answers"] = [dict(a) for a in answers]
            submissions.append(item)
        return submissions
    finally:
        conn.close()


def get_stats(db_path=None):
    """Aggregate feedback for the seller dashboard.

    Returns a dict:
        {
          "total": int,
          "by_category": {category: count, ...},
          "reasons_by_category": {category: [{"reason": str, "count": int}, ...]}
        }
    """
    conn = get_connection(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()["c"]

        cat_rows = conn.execute(
            "SELECT category, COUNT(*) AS c FROM submissions "
            "GROUP BY category ORDER BY c DESC"
        ).fetchall()
        by_category = {r["category"]: r["c"] for r in cat_rows}

        reason_rows = conn.execute(
            """SELECT category, final_reason AS reason, COUNT(*) AS c
               FROM submissions
               WHERE final_reason IS NOT NULL AND final_reason != ''
               GROUP BY category, final_reason
               ORDER BY category, c DESC"""
        ).fetchall()
        reasons_by_category = {}
        for r in reason_rows:
            reasons_by_category.setdefault(r["category"], []).append(
                {"reason": r["reason"], "count": r["c"]}
            )

        return {
            "total": total,
            "by_category": by_category,
            "reasons_by_category": reasons_by_category,
        }
    finally:
        conn.close()


def get_investigation(db_path=None):
    """Build the Issue Investigation report.

    For every product that has at least one return, break the returns down by
    the specific problem the customer reported (the most detailed answer in the
    path), and compute a real defect rate against units sold.

    Returns a dict:
        {
          "products": [
            {
              "product_id": str,
              "model": str,
              "category": str,
              "units_sold": int,
              "total_returns": int,
              "return_rate_pct": float,   # total_returns / units_sold * 100
              "issues": [
                 {
                   "problem": str,              # specific reported problem
                   "count": int,                # customers reporting it
                   "defect_rate_pct": float,    # count / units_sold * 100
                   "share_of_returns_pct": float  # count / total_returns * 100
                 }, ...
              ]
            }, ...
          ],
          "category_avg_defect_rate": {category: pct, ...}  # for comparison
        }
    """
    conn = get_connection(db_path)
    try:
        # Catalog of products with sales volume.
        prod_rows = conn.execute(
            "SELECT id, model, category, units_sold FROM products"
        ).fetchall()
        products = {r["id"]: dict(r) for r in prod_rows}

        # Count returns per product.
        total_rows = conn.execute(
            """SELECT product_id, COUNT(*) AS c
               FROM submissions
               WHERE product_id IS NOT NULL AND product_id != ''
               GROUP BY product_id"""
        ).fetchall()
        totals = {r["product_id"]: r["c"] for r in total_rows}

        # The "specific problem" is the most detailed answer in a submission:
        # the last answer row (the shared closing question is excluded so the
        # problem reflects the actual issue, not the recommend question).
        issue_rows = conn.execute(
            """SELECT s.product_id AS pid, a.answer_value AS problem, COUNT(*) AS c
               FROM submissions s
               JOIN answers a ON a.submission_id = s.id
               WHERE s.product_id IS NOT NULL AND s.product_id != ''
                 AND a.question_id NOT IN ('recommend')
                 AND a.id = (
                     SELECT MAX(a2.id) FROM answers a2
                     WHERE a2.submission_id = s.id
                       AND a2.question_id NOT IN ('recommend')
                 )
               GROUP BY s.product_id, a.answer_value
               ORDER BY c DESC"""
        ).fetchall()

        issues_by_product = {}
        for r in issue_rows:
            issues_by_product.setdefault(r["pid"], []).append(
                {"problem": r["problem"], "count": r["c"]}
            )

        result_products = []
        # Accumulators for category-average defect rate.
        cat_returns = {}
        cat_units = {}

        for pid, prod in products.items():
            total_returns = totals.get(pid, 0)
            units = prod["units_sold"] or 0
            cat = prod["category"]

            cat_returns[cat] = cat_returns.get(cat, 0) + total_returns
            # Count each product's units once toward its category.
            cat_units[cat] = cat_units.get(cat, 0) + units

            if total_returns == 0:
                continue  # only surface products that actually have returns

            return_rate = (total_returns / units * 100) if units else 0.0
            issues = []
            for item in issues_by_product.get(pid, []):
                count = item["count"]
                issues.append(
                    {
                        "problem": item["problem"],
                        "count": count,
                        "defect_rate_pct": round((count / units * 100), 2) if units else 0.0,
                        "share_of_returns_pct": round((count / total_returns * 100), 1),
                    }
                )
            issues.sort(key=lambda x: x["count"], reverse=True)

            result_products.append(
                {
                    "product_id": pid,
                    "model": prod["model"],
                    "category": cat,
                    "category_name": question_catalog.CATEGORY_NAMES.get(cat, cat),
                    "units_sold": units,
                    "total_returns": total_returns,
                    "return_rate_pct": round(return_rate, 2),
                    "issues": issues,
                }
            )

        result_products.sort(key=lambda p: p["return_rate_pct"], reverse=True)

        category_avg = {
            cat: round((cat_returns[cat] / cat_units[cat] * 100), 2)
            for cat in cat_returns
            if cat_units.get(cat)
        }

        return {
            "products": result_products,
            "category_avg_defect_rate": category_avg,
        }
    finally:
        conn.close()
