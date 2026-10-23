"""SQLite data layer for Return Radar.

Stores return-feedback submissions and their individual answers, each tagged
with the product category so sellers can analyze why products come back.
"""
import sqlite3
import os
from datetime import datetime, timezone

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
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                category     TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                final_reason TEXT
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

            CREATE INDEX IF NOT EXISTS idx_submissions_category
                ON submissions(category);
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_submission(category, answers, final_reason=None, db_path=None):
    """Persist a completed submission plus its answers.

    Args:
        category: product category string.
        answers: list of dicts with keys question_id, question_text, answer_value.
        final_reason: short summary of the primary return reason (optional).

    Returns:
        The new submission id.
    """
    conn = get_connection(db_path)
    try:
        created_at = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO submissions (category, created_at, final_reason) VALUES (?, ?, ?)",
            (category, created_at, final_reason),
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
