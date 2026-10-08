"""Impact analysis (keyword matching MVP).

Har requirement change ke liye project ki files me wo lines dhundta hai
jo change se jude lagte hain, aur har line ka evidence deta hai.
"""
import re
from pathlib import Path

from .drift import extract_quantities, key_words

MAX_FILES = 10
MAX_EVIDENCE = 5

# Ek unit ki value code me dusre unit me bhi likhi ho sakti hai (10 minutes = 600 seconds)
CONVERSIONS = {
    "seconds": [("ms", 1000)],
    "minutes": [("seconds", 60), ("ms", 60000)],
    "hours": [("minutes", 60), ("seconds", 3600), ("ms", 3600000)],
    "days": [("hours", 24), ("seconds", 86400)],
    "weeks": [("days", 7)],
}

DEF_RE = re.compile(r"^(\s*)(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:def|function)\s+(\w+)")


def kind_of(path: str) -> str:
    name = Path(path).name.lower()
    if name.startswith("test_") or "_test." in name or ".test." in name or ".spec." in name:
        return "test"
    if Path(path).suffix.lower() in {".md", ".txt"}:
        return "doc"
    return "code"


def line_stems(line: str) -> set[str]:
    """Line ke shabd (camelCase aur snake_case todkar), pehle 5 akshar."""
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", line)
    return {w.lower()[:5] for w in re.findall(r"[A-Za-z]+", spaced) if len(w) >= 3}


def enclosing_functions(lines: list[str]) -> list[str | None]:
    """Har line ke liye batata hai ki wo kis function ke andar hai."""
    result: list[str | None] = []
    current: tuple[int, str] | None = None
    for line in lines:
        match = DEF_RE.match(line)
        if match:
            current = (len(match.group(1)), match.group(2))
        elif line.strip() and current is not None:
            indent = len(line) - len(line.lstrip())
            if indent <= current[0]:
                current = None
        result.append(current[1] if current else None)
    return result


def number_pattern(num: float) -> tuple[str, re.Pattern]:
    text = str(int(num)) if float(num).is_integer() else str(num)
    return text, re.compile(rf"(?<![\w.]){re.escape(text)}(?![\w]|\.\d)")


def literal_variants(change: dict) -> list[tuple[re.Pattern, str]]:
    """Old value code me kin roopon me likhi ho sakti hai."""
    old_value = change.get("old_value")
    if change.get("type") != "value_change" or not old_value:
        return []
    quantities = extract_quantities(old_value)
    if not quantities:
        return []
    q = quantities[0]

    variants: list[tuple[float, str]] = []
    for to_unit, factor in CONVERSIONS.get(q.unit, []):
        variants.append((q.value * factor, f"= {old_value} in {to_unit}"))
    variants.append((q.value, "old value"))  # raw number sabse aakhir me

    result = []
    for num, note in variants:
        text, pattern = number_pattern(num)
        result.append((pattern, f"{text} ({note})"))
    return result


def find_literal(line: str, variants: list[tuple[re.Pattern, str]]) -> str | None:
    for pattern, description in variants:
        if pattern.search(line):
            return description
    return None


def impact_for_change(files: list[dict], change: dict) -> list[dict]:
    sentence = change.get("old_sentence") or change.get("new_sentence") or ""
    words = [w for w in key_words(sentence, extract_quantities(sentence)) if len(w) >= 3]
    if not words:
        return []

    stem_to_word = {w[:5]: w for w in words}
    stems = set(stem_to_word)
    min_matches = 2 if len(stems) >= 2 else 1
    literals = literal_variants(change)

    impacted: list[dict] = []
    for f in files:
        lines = f["content"].splitlines()
        functions = enclosing_functions(lines)
        hits: list[dict] = []
        for i, line in enumerate(lines):
            matched = stems & line_stems(line)
            literal = find_literal(line, literals)
            count = len(matched)
            if count >= min_matches or (count >= 1 and literal):
                hits.append({
                    "line": i + 1,
                    "text": line.strip()[:120],
                    "function": functions[i],
                    "matched": sorted(stem_to_word[s] for s in matched),
                    "literal": literal,
                    "score": count + (2 if literal else 0),
                })
        if not hits:
            continue
        hits.sort(key=lambda h: (-h["score"], h["line"]))
        top = hits[:MAX_EVIDENCE]
        impacted.append({
            "path": f["path"],
            "kind": kind_of(f["path"]),
            "score": sum(h["score"] for h in top),
            "evidence": top,
        })

    impacted.sort(key=lambda x: -x["score"])
    return impacted[:MAX_FILES]


def analyze_impact(files: list[dict], changes: list[dict]) -> list[dict]:
    """files = [{'path': ..., 'content': ...}], changes = detect_drift() ka output."""
    return [{"change": c, "files": impact_for_change(files, c)} for c in changes]