"""Top-5 recall benchmark for function-level matching.

Run from the backend folder:
    python benchmark/run_benchmark.py
    python benchmark/run_benchmark.py --repo path/to/other_repo --cases path/to/cases.json

A case is a HIT when at least one expected unit ("file.py::qualname") appears
in the top-5 results. If "expected" is empty the requirement has no code, and the
case is a HIT only when no HIGH-confidence match is returned. Recall@5 = hits / cases.

Two modes are compared on the same cases:
  baseline = words in names/comments only (no numbers, no synonyms, no constants)
  full     = all signals (what the app uses)

--min-score 4 shows only medium/high confidence matches, like the website does.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.astmatch import build_index, rank_units  # noqa: E402

HERE = Path(__file__).resolve().parent


def load_repo(repo: Path):
    files = []
    for p in sorted(repo.rglob("*")):
        if p.is_file() and p.suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
            files.append((str(p.relative_to(repo)).replace("\\", "/"),
                          p.read_text(encoding="utf-8", errors="ignore")))
    return files


def run(units, cases, k, min_score=0.0, meaning=False, **flags):
    hits, rows, top1 = 0, [], [0]
    for c in cases:
        # meaning mode: the old sentence is what the existing code implements, so it is the search text
        qt = c.get("old", "") if meaning else ""
        top = rank_units(units, c["entity"], c["property"], c["old_value"], top_k=k, min_score=min_score,
                         query_text=qt, use_meaning=meaning, **flags)
        found = [f"{m.unit.path}::{m.unit.qualname}" for m in top]
        if c["expected"]:
            ok = any(e in found for e in c["expected"])
        else:  # "unsupported requirement": correct = nothing confidently matched
            ok = not any(m.confidence == "high" for m in top)
        hits += ok
        if c["expected"] and found and found[0] in c["expected"]:
            top1[0] += 1
        rows.append((c["id"], ok, found))
    return hits, rows, top1[0]              


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(HERE / "mini_repo"))
    ap.add_argument("--cases", default=str(HERE / "cases.json"))
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-score", type=float, default=0.0, help="hide matches below this score (website uses 4)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    cases = json.loads(Path(a.cases).read_text(encoding="utf-8"))
    units = build_index(load_repo(Path(a.repo)))
    print(f"Indexed {len(units)} units from {a.repo}; {len(cases)} cases; k={a.k}; min-score={a.min_score}\n")

    modes = {
        "baseline (names/words only)": dict(use_literals=False, use_synonyms=False, use_constants=False),
        "full (AST + literals + synonyms)": dict(),
    }

    from app.services.embed import get_embedder
    if get_embedder() is not None:
        modes["full + meaning (embeddings)"] = dict(meaning=True)
    else:
        print("(embeddings not available: install fastembed or sentence-transformers to see the 'meaning' row)\n")
    for label, flags in modes.items():
        hits, rows, top1 = run(units, cases, a.k, a.min_score, **flags)
        labelled = sum(1 for c in cases if c["expected"])
        print(f"{label:36s} recall@{a.k} = {hits}/{len(cases)} = {hits / len(cases):.0%}"
              f"   | rank-1 correct = {top1}/{labelled}")
        if a.verbose:
            for cid, ok, found in rows:
                print(f"   case {cid}: {'HIT ' if ok else 'MISS'} {found}")
    print("\nMISS rows (full mode) show where to improve the matcher.")


if __name__ == "__main__":
    main()