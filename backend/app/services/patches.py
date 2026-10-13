"""Suggested edits (Build 13).

For a requirement change that swaps one number for another (20% -> 30%, 10 minutes -> 5 minutes),
show the exact code line that holds the old number and what it would look like with the new one.
DriftAI never edits files. These are suggestions for a person to review.
"""
from __future__ import annotations

from app.services.drift import extract_quantities
from app.services.impact import CONVERSIONS, number_pattern

TEXT_STARTS = ("#", "//", "*", "/*", '"', "'")


def _fmt(num: float) -> str:
    num = round(float(num), 6)
    return str(int(num)) if num.is_integer() else str(num)


def _first_quantity(text):
    found = extract_quantities(str(text or ""))
    return found[0] if found else None


def _variants(old_q, new_q) -> list[tuple[float, float, str]]:
    """(number in code, number to write instead, note). Unit conversions come before the plain number."""
    out: list[tuple[float, float, str]] = []
    for to_unit, factor in CONVERSIONS.get(old_q.unit, []):
        out.append((old_q.value * factor, new_q.value * factor, f"written in {to_unit}"))
    out.append((old_q.value, new_q.value, ""))
    return out


def _edits_for(unit, variants, confidence: str, seen: set) -> list[dict]:
    edits = []
    for offset, line in enumerate(unit.source.splitlines()):
        lineno = unit.start + offset
        key = (unit.path, lineno)
        if key in seen:
            continue
        for code_num, new_num, note in variants:
            text, pattern = number_pattern(code_num)
            hits = pattern.findall(line)
            if not hits:
                continue
            after = pattern.sub(_fmt(new_num), line, count=1)
            extra = []
            if note:
                extra.append(note)
            if len(hits) > 1:
                extra.append("the number appears more than once on this line; only the first is changed")
            seen.add(key)
            edits.append({
                "path": unit.path, "line": lineno, "qualname": unit.qualname,
                "confidence": confidence,
                "kind": "text" if line.strip().startswith(TEXT_STARTS) else "code",
                "before": line.rstrip(), "after": after.rstrip(),
                "note": "; ".join(extra),
            })
            break
    return edits


def suggest_patches(units, fn_items: list[dict]) -> list[dict]:
    """fn_items = the output of functions_for_changes(). Returns one entry per change."""
    by_key = {(u.path, u.qualname): u for u in units}
    out: list[dict] = []
    for item in fn_items:
        entry = {"entity": item["entity"], "property": item["property"],
                 "old_value": item["old_value"], "new_value": item["new_value"],
                 "edits": [], "note": ""}
        old_q, new_q = _first_quantity(item["old_value"]), _first_quantity(item["new_value"])
        if old_q is None or new_q is None:
            entry["note"] = "This change has no old and new number, so no edit is suggested."
        elif old_q.unit != new_q.unit:
            entry["note"] = "The unit changed, so please update the code by hand."
        elif not item["matches"]:
            entry["note"] = "No strong match was found, so no edit is suggested."
        else:
            variants = _variants(old_q, new_q)
            seen: set = set()
            for m in item["matches"]:
                unit = by_key.get((m["path"], m["qualname"]))
                if unit is not None:
                    entry["edits"].extend(_edits_for(unit, variants, m["confidence"], seen))
            if not entry["edits"]:
                entry["note"] = "The old number was not found as a plain number in the matched code."
        out.append(entry)
    return out
