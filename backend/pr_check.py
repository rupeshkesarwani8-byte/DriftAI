"""Build 12: check a pull request for requirement changes and list the functions they probably affect.

It needs no server and no database. A GitHub Action runs it (see .github/workflows/driftai.yml),
or you can run it by hand inside any git repository:

    python pr_check.py --base origin/main --head HEAD
    python pr_check.py --base origin/main --head HEAD --req "REQUIREMENTS.md,docs/requirements*.md" --out comment.md

It compares every changed requirement file (old text from --base, new text from --head), finds what
changed with DriftAI's drift detector, then ranks the repository's functions with the AST matcher.
The result is written as Markdown (to --out, or to the screen).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("DRIFTAI_EMBEDDINGS", "off")   # keep the check fast; set it to "on" to use meaning-matching

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.astmatch import STRONG_SCORE, build_index, rank_units  # noqa: E402
from app.services.drift import detect_drift  # noqa: E402

MARKER = "<!-- driftai-pr-comment -->"
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
SKIP_DIRS = {".git", ".driftai", "samples", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", "benchmark", "tests", "test"}
DEFAULT_REQ = "REQUIREMENTS.md,docs/requirements*.md,docs/REQUIREMENTS*.md"
MAX_FILES = 400
MAX_CHANGES = 8


def git(*args: str, cwd: str = ".") -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def changed_requirement_files(base: str, head: str, patterns: list[str], cwd: str) -> list[str]:
    names = git("diff", "--name-only", base, head, cwd=cwd).splitlines()
    return [n for n in names if any(fnmatch.fnmatch(n, p) for p in patterns)]


def read_at(ref: str, path: str, cwd: str) -> str:
    try:
        return git("show", f"{ref}:{path}", cwd=cwd)
    except RuntimeError:        # the file did not exist at that point
        return ""


def load_code(root: str) -> list[tuple[str, str]]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if p.suffix in CODE_SUFFIXES:
                rel = str(p.relative_to(root)).replace("\\", "/")
                files.append((rel, p.read_text(encoding="utf-8", errors="ignore")))
                if len(files) >= MAX_FILES:
                    return files
    return files


def field(obj, *names, default=""):
    for n in names:
        v = obj.get(n) if isinstance(obj, dict) else getattr(obj, n, None)
        if v not in (None, ""):
            return v
    return default


def analyse(old_text: str, new_text: str, units) -> list[dict]:
    """Return one dict per requirement change, each with its strongest matching functions."""
    out = []
    for ch in detect_drift(old_text, new_text)[:MAX_CHANGES]:
        entity = str(field(ch, "entity"))
        prop = str(field(ch, "property", "prop"))
        old_v = str(field(ch, "old_value", "old"))
        new_v = str(field(ch, "new_value", "new"))
        sentence = str(field(ch, "old_sentence", "new_sentence"))
        ranked = rank_units(units, entity, prop, old_v, top_k=20, query_text=sentence)
        strong = [m for m in ranked if m.score >= STRONG_SCORE][:5]
        out.append({"entity": entity, "property": prop, "old": old_v, "new": new_v, "matches": strong})
    return out


def render(results: dict[str, list[dict]], notes: list[str]) -> str:
    lines = [MARKER, "## DriftAI: requirement change check", ""]
    if not results:
        lines.append("No requirement files were changed in this pull request, so there is nothing to check.")
    for path, changes in results.items():
        lines.append(f"### `{path}`")
        if not changes:
            lines += ["", "No meaningful requirement change was found in this file.", ""]
            continue
        for c in changes:
            what = f"**{c['entity'] or 'requirement'}**" + (f" / {c['property']}" if c["property"] else "")
            lines += ["", f"- {what}: `{c['old'] or '-'}` → `{c['new'] or '-'}`"]
            if not c["matches"]:
                lines.append("  - No function matched with medium or high confidence. Please check the code by hand.")
            for m in c["matches"]:
                why = "; ".join(m.reasons[:2])
                lines.append(f"  - `{m.unit.path}` → `{m.unit.qualname}` (lines {m.unit.start}-{m.unit.end}), "
                             f"confidence **{m.confidence}**" + (f" - {why}" if why else ""))
        lines.append("")
    for n in notes:
        lines.append(f"> {n}")
    lines += ["", "_DriftAI matches by names, comments, numbers and synonyms. Treat this as a checklist of places to look, not as proof._"]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="git ref of the old version, e.g. origin/main")
    ap.add_argument("--head", default="HEAD", help="git ref of the new version (default HEAD)")
    ap.add_argument("--repo", default=".", help="path of the repository to check (default: current folder)")
    ap.add_argument("--req", default=os.environ.get("DRIFTAI_REQ_FILES", DEFAULT_REQ),
                    help="comma-separated patterns of requirement files")
    ap.add_argument("--out", default="", help="write the Markdown here instead of printing it")
    a = ap.parse_args(argv)

    patterns = [p.strip() for p in a.req.split(",") if p.strip()]
    files = changed_requirement_files(a.base, a.head, patterns, a.repo)
    notes: list[str] = []
    results: dict[str, list[dict]] = {}
    if files:
        units = build_index(load_code(a.repo))
        if not units:
            notes.append("No Python or JavaScript code was found, so no functions could be matched.")
        for f in files:
            old = read_at(a.base, f, a.repo)
            new = read_at(a.head, f, a.repo)
            if not old.strip():
                notes.append(f"`{f}` is a new file, so there is no earlier version to compare.")
                continue
            results[f] = analyse(old, new, units)
    md = render(results, notes)
    if a.out:
        Path(a.out).write_text(md, encoding="utf-8")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())