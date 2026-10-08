"""List every function / constant DriftAI can see in a folder, with its exact name.

Use it when you write your own benchmark cases: copy the names into "expected".

Run from the backend folder:
    python benchmark/list_units.py benchmark/requests_repo
    python benchmark/list_units.py benchmark/requests_repo --grep redirect
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.astmatch import build_index  # noqa: E402
from benchmark.run_benchmark import load_repo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--grep", default="", help="show only names containing this text")
    a = ap.parse_args()
    units = build_index(load_repo(Path(a.repo)))
    shown = 0
    for u in units:
        name = f"{u.path}::{u.qualname}"
        if a.grep.lower() in name.lower():
            print(f"{name}   [{u.kind}, line {u.start}]")
            shown += 1
    print(f"\n{shown} of {len(units)} units shown")


if __name__ == "__main__":
    main()