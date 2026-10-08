# DriftAI

DriftAI finds **requirement drift**. You give it the old and the new version of a requirement and your code. It tells you what changed, which files and exact functions are affected, and gives a prioritised action plan with a risk score.

## Features

- **Drift detection**: finds changed numbers, units and rules between two versions of a requirement.
- **Impact analysis**: shows the affected files and the exact functions or constants (Python AST based), ranked by confidence, with the evidence for each match.
- **Action plan and risk score**: ordered to-do list, exportable as Markdown.
- **GitHub import**: paste a public repository link to load its code.
- **Impact graph**: requirement change → file → function, drawn with React Flow.
- **Accounts**: signup and login (scrypt-hashed passwords, signed tokens).
- **History and feedback**: saved analyses, with thumbs feedback on results.

## Tech stack

React (Vite), React Router, React Flow, Python FastAPI, SQLAlchemy, SQLite.

## Run it (Windows)

Backend, in one terminal:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install httpx
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Tests and benchmark

```powershell
cd backend
pytest -v
python benchmark/run_benchmark.py --repo benchmark/requests_repo --cases benchmark/requests_cases.json -v
```

Download the benchmark repository first:

```powershell
python benchmark/fetch_repo.py https://github.com/psf/requests benchmark/requests_repo --only src/requests
```

Results so far (small, hand-written cases, so treat them as a sanity check, not as a measured accuracy):

| Set | Cases | recall@5 | rank-1 |
|---|---|---|---|
| Mini repo | 12 | 12/12 | 11/11 |
| psf/requests (author-written) | 9 | 9/9 | 6/8 |
| psf/requests (hard cases) | 6 | 6/6 | 2/5 |

## Known limitations

- Matching uses names, comments, numbers and a small synonym table. It does not understand meaning.
- Only module-level constants and functions are indexed. JavaScript indexing is approximate.
- Behaviour-style requirements often rank the right function 2nd to 4th, not 1st.
- Private GitHub repositories are not supported, and the GitHub API is used without a key (rate limited).
- Accounts exist, but projects and analyses are not yet separated per user.