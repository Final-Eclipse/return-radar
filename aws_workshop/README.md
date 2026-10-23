# Return Radar

An adaptive product return feedback system. Customers answer a short,
accessible questionnaire that **branches based on product category and their
previous answers**, and every submission is stored in a SQL database tagged
with its category. Sellers get a dashboard that aggregates the reasons behind
returns.

Built for a Kiro workshop. No external services, no sign-ups, no API keys —
it runs entirely on your machine.

## Stack

- **Backend:** Python + Flask
- **Database:** SQLite (via the standard-library `sqlite3` module — zero setup)
- **Frontend:** Plain HTML/CSS + vanilla JavaScript (no build step)
- **Charts:** Pure CSS bars (no external chart libraries)

The adaptive logic is **backend-driven**: after each answer the browser asks
the Python server for the next question, so the branching lives in Python.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) seed sample data so the dashboard looks alive
python seed.py

# 3. Run the app
python app.py
```

Then open http://localhost:5000

- **/** — customer questionnaire
- **/dashboard** — seller dashboard

## How the adaptive flow works

1. The customer picks a product category (8 available).
2. The browser sends `{category, answers_so_far}` to `POST /next-question`.
3. Python (`questions.py`) walks a per-category question tree and returns the
   next question, or a completion signal. Each category branches 3–4 levels
   deep depending on earlier answers.
4. On completion the browser calls `POST /submit`, and the full answer trail +
   primary reason + category are written to SQLite.

## Project layout

```
app.py            Flask app: pages + API endpoints
questions.py      Product categories + adaptive question engine
database.py       SQLite schema and data-access layer
seed.py           Loads sample submissions for a demo
templates/        index.html (questionnaire), dashboard.html
static/           style.css, app.js (questionnaire), dashboard.js
test_app.py       Tests for DB, engine, and endpoints
```

## Data model (SQLite)

- `submissions`: `id`, `category`, `created_at`, `final_reason`
- `answers`: `id`, `submission_id` (FK → submissions), `question_id`,
  `question_text`, `answer_value`

## Accessibility

- Semantic HTML with `fieldset`/`legend` radio groups and associated `<label>`s
- Full keyboard operability and visible focus rings (never removed)
- `aria-live` regions announce each new question and status messages
- Focus moves to each new question for screen-reader users
- A skip link to main content
- Color palette checked for WCAG AA text contrast; information is never
  conveyed by color alone (bars also show numeric counts)
- Honors `prefers-reduced-motion`

> Note: automated/keyboard accessibility is covered here. Full WCAG conformance
> still requires manual testing with assistive technologies.

## Tests

```bash
python -m pytest -q
```

Covers the database layer (category association preserved, aggregation), the
adaptive engine (branching, termination), and the HTTP endpoints (including a
full questionnaire run that lands a row in the database).
```
