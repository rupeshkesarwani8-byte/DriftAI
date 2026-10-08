"""Download a public GitHub repo into a local folder so the benchmark can run on real code.

Run from the backend folder:
    python benchmark/fetch_repo.py https://github.com/psf/requests benchmark/requests_repo --only src/requests

--only keeps just one sub-folder (and removes that prefix from the saved paths),
so file names look like "models.py", the same way requests_cases.json names them.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.github_import import GitHubImportError, fetch_repo_files  # noqa: E402


def main(argv=None, fetch=fetch_repo_files):
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--only", default="", help="keep only this sub-folder, e.g. src/requests")
    ap.add_argument("--branch", default=None)
    a = ap.parse_args(argv)

    try:
        ref, files, stats = fetch(a.url, a.branch)
    except GitHubImportError as e:
        print("Error:", e)
        return 1

    prefix = a.only.strip("/")
    out = Path(a.out)
    saved = 0
    for path, text in files:
        if prefix:
            if not path.startswith(prefix + "/"):
                continue
            path = path[len(prefix) + 1:]
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        saved += 1
    print(f"Saved {saved} files from {ref.owner}/{ref.repo} into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())