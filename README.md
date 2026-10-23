# Return Radar

> An adaptive product return feedback system — built as part of the **AWS Kiro Challenge**.

Customers answer a short, branching questionnaire explaining why they're returning a product. Every submission is stored in a database and surfaced on a seller dashboard that aggregates return reasons by category, helping sellers understand what's actually driving returns.

---

## Features

- **Adaptive questionnaire** — the question flow branches 3–4 levels deep depending on the product category and prior answers. The branching logic lives entirely on the server, so the browser never sees the full question tree.
- **8 product categories** — Clothing & Apparel, Electronics, Home & Kitchen, Beauty & Health, Toys & Games, Footwear, Books & Media, and Sporting Goods, each with their own tailored question paths.
- **Seller dashboard** — aggregated stat cards, pure-CSS bar charts of top return reasons per category, and a full submissions table.
- **Accessible by default** — semantic HTML, keyboard-operable radio groups, `aria-live` announcements, programmatic focus management, WCAG AA colour contrast, and `prefers-reduced-motion` support.
- **Zero external dependencies** — SQLite for storage, no cloud services, no API keys, no build step.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 + Flask 3.1.0 |
| Database | SQLite (Python stdlib `sqlite3`) |
| Frontend | HTML + CSS + vanilla JavaScript |
| Charts | Pure CSS bar charts |
| Testing | pytest 8.3.4 |
| Templates | Jinja2 (bundled with Flask) |

---

## Quick Start

```bash
# From the aws_workshop/ directory

# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) seed demo data so the dashboard looks populated
python seed.py

# 3. Start the server
python app.py
# → http://localhost:5000
```

| URL | Description |
|---|---|
| `http://localhost:5000/` | Customer questionnaire |
| `http://localhost:5000/dashboard` | Seller analytics dashboard |

---

## Project Structure

```
aws_workshop/
├── app.py            # Flask app — all routes and startup
├── questions.py      # Adaptive question engine + category definitions
├── database.py       # SQLite schema and data-access layer
├── seed.py           # Seeds sample submissions for demos
├── requirements.txt
├── templates/
│   ├── index.html    # Customer questionnaire shell (3-step flow)
│   └── dashboard.html
├── static/
│   ├── app.js        # Questionnaire frontend (category → questions → done)
│   ├── dashboard.js  # Dashboard frontend (fetch /stats → render charts + table)
│   └── style.css
└── test_app.py       # pytest suite covering DB, engine, and endpoints
```

---

## How the Adaptive Flow Works

1. The customer selects a product category from the grid.
2. The browser posts `{ category, answers }` to `POST /next-question`.
3. The Python engine (`questions.py`) walks the category's question tree and returns the next applicable question, or `{ "done": true }` when the flow is complete.
4. On completion the browser posts to `POST /submit`. The server validates the submission is complete, converts raw answer values to human-readable labels, and writes the full answer trail plus a primary reason summary to SQLite.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Customer questionnaire page |
| `GET` | `/dashboard` | Seller dashboard page |
| `GET` | `/categories` | JSON list of all product categories |
| `POST` | `/next-question` | Returns the next question or `{ "done": true }` |
| `POST` | `/submit` | Validates and persists a completed submission |
| `GET` | `/stats` | Aggregated stats and all submissions for the dashboard |

---

## Data Model

```
submissions
  id           INTEGER  PRIMARY KEY
  category     TEXT     e.g. "Clothing & Apparel"
  created_at   TEXT     ISO 8601 UTC
  final_reason TEXT     Primary return reason label

answers
  id            INTEGER  PRIMARY KEY
  submission_id INTEGER  FK → submissions(id) ON DELETE CASCADE
  question_id   TEXT     e.g. "reason", "fit_issue"
  question_text TEXT     Full question as shown to the customer
  answer_value  TEXT     Human-readable option label
```

---

## Running Tests

```bash
cd aws_workshop
python -m pytest -q
```

The test suite spins up an isolated in-memory SQLite database and a Flask test client — it does not touch the real `return_radar.db`. Tests cover the database layer, the adaptive engine (branching and termination), and all HTTP endpoints including a full end-to-end questionnaire run.

---

## Accessibility

- Semantic `<fieldset>`/`<legend>` radio groups with associated `<label>`s
- Full keyboard operability and always-visible focus rings
- `aria-live="polite"` region announces each new question; `aria-live="assertive"` announces errors
- Focus moves programmatically to each new question for screen-reader users
- Skip link to main content
- WCAG AA text contrast throughout; data is never conveyed by colour alone (bar charts include numeric counts)
- Respects `prefers-reduced-motion`

> Full WCAG conformance requires manual testing with assistive technologies beyond what automated checks cover.

---

## License

See [LICENSE](LICENSE).
