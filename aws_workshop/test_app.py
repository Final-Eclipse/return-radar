"""Tests for Return Radar: database layer, adaptive engine, and endpoints."""
import os
import tempfile

import pytest

import database
import questions
import app as app_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def temp_db():
    """Provide a fresh temporary SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.init_db(path)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def client(temp_db, monkeypatch):
    """Flask test client pointed at a temporary database."""
    # Route the app's data layer at the temp DB by patching DB_PATH default.
    monkeypatch.setattr(database, "DB_PATH", temp_db)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Task 2: database layer
# ---------------------------------------------------------------------------
def test_save_and_get_submission_preserves_category(temp_db):
    answers = [
        {"question_id": "reason", "question_text": "Why?", "answer_value": "It didn't fit"},
        {"question_id": "fit_issue", "question_text": "How?", "answer_value": "Too small"},
    ]
    sid = database.save_submission(
        category="Clothing & Apparel",
        answers=answers,
        final_reason="It didn't fit",
        db_path=temp_db,
    )
    assert sid > 0

    row = database.get_submission(sid, db_path=temp_db)
    assert row is not None
    assert row["category"] == "Clothing & Apparel"
    assert row["final_reason"] == "It didn't fit"
    assert len(row["answers"]) == 2
    assert row["answers"][0]["answer_value"] == "It didn't fit"


def test_get_stats_aggregates_by_category_and_reason(temp_db):
    database.save_submission("Electronics", [], "Item is defective / not working", db_path=temp_db)
    database.save_submission("Electronics", [], "Item is defective / not working", db_path=temp_db)
    database.save_submission("Electronics", [], "Not as described", db_path=temp_db)
    database.save_submission("Footwear", [], "Didn't fit", db_path=temp_db)

    stats = database.get_stats(db_path=temp_db)
    assert stats["total"] == 4
    assert stats["by_category"]["Electronics"] == 3
    assert stats["by_category"]["Footwear"] == 1

    elec_reasons = {r["reason"]: r["count"] for r in stats["reasons_by_category"]["Electronics"]}
    assert elec_reasons["Item is defective / not working"] == 2
    assert elec_reasons["Not as described"] == 1


# ---------------------------------------------------------------------------
# Task 3: adaptive engine
# ---------------------------------------------------------------------------
def test_first_question_is_reason_for_every_category():
    for cat in questions.CATEGORY_IDS:
        result = questions.get_next_question(cat, {})
        assert result["done"] is False
        assert result["question"]["id"] == "reason"


def test_branching_depends_on_reason_answer():
    # Clothing + "fit" leads to the fit_issue question.
    result = questions.get_next_question("clothing", {"reason": "fit"})
    assert result["question"]["id"] == "fit_issue"

    # Clothing + "quality" leads to the quality_detail question instead.
    result = questions.get_next_question("clothing", {"reason": "quality"})
    assert result["question"]["id"] == "quality_detail"


def test_full_path_terminates_with_done():
    # Walk a full electronics path to completion.
    answers = {}
    cat = "electronics"
    seen = []
    for _ in range(10):  # safety bound
        result = questions.get_next_question(cat, answers)
        if result["done"]:
            break
        q = result["question"]
        seen.append(q["id"])
        # Always pick the first option, but choose "defective" for reason to branch.
        if q["id"] == "reason":
            answers[q["id"]] = "defective"
        else:
            answers[q["id"]] = q["options"][0]["value"]
    else:
        pytest.fail("Flow did not terminate")

    assert result["done"] is True
    assert "reason" in seen
    assert "defect_type" in seen  # branch was taken
    assert "recommend" in seen    # shared closing question asked


def test_unknown_category_raises():
    with pytest.raises(ValueError):
        questions.get_next_question("nope", {})


def test_summarize_and_records_use_labels():
    answers = {"reason": "fit", "fit_issue": "too_small"}
    assert questions.summarize_reason("clothing", answers) == "It didn't fit"
    records = questions.build_answer_records("clothing", answers)
    ids = [r["question_id"] for r in records]
    assert ids == ["reason", "fit_issue"]
    assert records[1]["answer_value"] == "Too small"


# ---------------------------------------------------------------------------
# Task 4 & 6: endpoints
# ---------------------------------------------------------------------------
def test_categories_endpoint(client):
    resp = client.get("/categories")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 8


def test_next_question_endpoint_branches(client):
    resp = client.post("/next-question", json={"category": "clothing", "answers": {}})
    assert resp.status_code == 200
    assert resp.get_json()["question"]["id"] == "reason"

    resp = client.post(
        "/next-question",
        json={"category": "clothing", "answers": {"reason": "fit"}},
    )
    assert resp.get_json()["question"]["id"] == "fit_issue"


def test_next_question_rejects_bad_category(client):
    resp = client.post("/next-question", json={"category": "bogus", "answers": {}})
    assert resp.status_code == 400


def test_full_submission_flow_writes_to_db(client, temp_db):
    cat = "footwear"
    answers = {}
    # Drive the flow via the endpoint until done.
    for _ in range(10):
        resp = client.post("/next-question", json={"category": cat, "answers": answers})
        data = resp.get_json()
        if data["done"]:
            break
        q = data["question"]
        answers[q["id"]] = (
            "fit" if q["id"] == "reason" else q["options"][0]["value"]
        )

    resp = client.post("/submit", json={"category": cat, "answers": answers})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    sid = body["submission_id"]

    stored = database.get_submission(sid, db_path=temp_db)
    assert stored is not None
    assert stored["category"] == "Footwear"
    assert stored["final_reason"] == "Didn't fit"
    assert len(stored["answers"]) >= 2


def test_submit_rejects_incomplete_flow(client):
    # Only the first answer provided; flow is not complete.
    resp = client.post(
        "/submit", json={"category": "footwear", "answers": {"reason": "fit"}}
    )
    assert resp.status_code == 400


def test_stats_endpoint_after_submission(client, temp_db):
    database.save_submission("Toys & Games", [], "Broken / defective", db_path=temp_db)
    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["by_category"]["Toys & Games"] == 1
