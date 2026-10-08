# DriftAI

DriftAI finds out **what in your code is affected when a requirement changes**.
You paste the old and the new requirement, point it at a project (upload files or import a public GitHub repo), and it returns:

- what changed in the requirement (value, rule, scope),
- which files and which **functions** are probably affected, with a confidence level and the reason,
- a risk score, an action plan and a downloadable Markdown report.

## Features

| Area | What it does |
|---|---|
| Drift detection | Compares old vs new requirement text and lists each change |
| Function-level matching | Python `ast` indexes functions, methods and module constants; JS/TS use an approximate splitter |
| Impact graph | Interactive React Flow graph: change -> file -> function, click to highlight |
| Risk and plan | Risk level (low / medium / high) and an ordered action plan |
| GitHub import | Imports a public repository (unauthenticated GitHub API) |
| Accounts | Sign up / log in, scrypt password hashing, signed 7-day tokens, login lockout after 5 wrong passwords, change password |
| Per-user data | Every project and analysis belongs to its owner. Other users get 404 |
| Insights | Totals, risk levels, most analysed projects, recent analyses |
| Feedback | Mark a match relevant or not relevant |
| Reports | Markdown export of each analysis |
| Robustness | Error screen instead of a blank page, "server unreachable" banner, 404 page |

## How the matcher scores a function

| Signal | Score |
|---|---|
| Requirement word in the function / constant **name** | +3 (x word weight) |
| Word inside a compound name (`pool` in `POOLSIZE`) | +2 |
| Word in docstring or comments | +2 |
| Word in identifiers or strings | +1 |
| Old number found (`10 minutes` also looks for `600`) | +4 with word evidence, else +1 |
| Old `True` / `False` / `None` / short text found | +4 only with word evidence |
| A constant that is exactly the old value | extra boost |
| One function explains every requirement word | +2 (+1 if docstring says so) |

Rare words weigh more than common ones (range 0.6 to 1.4). Confidence: high >= 8, medium >= 4, otherwise low.

## Run it

Backend (terminal 1, folder `backend`):

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install httpx pytest
uvicorn app.main:app --reload
```

Frontend (terminal 2, folder `frontend`):

```
npm install
npm run dev
```

Open http://localhost:5173

## Tests

```
cd backend
pytest -v          # 63 tests
python benchmark/run_benchmark.py
python benchmark/run_benchmark.py --repo benchmark/requests_repo --cases benchmark/requests_cases.json
python benchmark/run_benchmark.py --repo benchmark/requests_repo --cases benchmark/hard_cases.json
```

## Benchmark (small, written by the author)

| Set | Cases | Recall@5 | Rank-1 correct |
|---|---|---|---|
| Mini repo | 12 | 12/12 | 11/11 |
| psf/requests | 9 | 9/9 | 8/8 |
| psf/requests, hard (behaviour-style) | 6 | 6/6 | 2/5 |

Recall@5 means the correct function is inside the top 5. The "baseline" mode (names and words only) scores lower on the same cases, which is why numbers, synonyms and constants are used.
A requirement with no matching code (a negative case) counts as correct only when no high-confidence match is returned.

## Known limitations

- The matcher is **heuristic** (names, comments, numbers, synonyms). It has no real understanding of meaning.
- Behaviour-style requirements often rank the right function 2nd to 4th, not 1st.
- The benchmarks are small and were written by the author, so they are an indication, not proof.
- Only functions and module-level constants are indexed. JS/TS indexing is approximate.
- Public repositories only. The GitHub API is unauthenticated, so it is rate limited.
- Login token is kept in browser `localStorage` (no refresh or revoke).
- Login lockout is kept in memory and resets when the server restarts.
- The first account created takes over projects that existed before accounts were added.
- Accounts live in `users.db`, projects in `driftai.db` (two SQLite files).

## Tech

FastAPI, SQLAlchemy 2, SQLite, Pydantic v2, Python `ast`, React 19, Vite, React Router, React Flow (`@xyflow/react`), pytest.