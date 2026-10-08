"""Evidence-backed action plan: impact results -> checklist."""

KIND_ORDER = {"code": 0, "test": 1, "doc": 2}


def _where(path: str, ev: dict) -> str:
    where = f"{path}:{ev['line']}"
    if ev.get("function"):
        where += f" ({ev['function']})"
    return where


def describe(change: dict, kind: str, path: str, ev: dict) -> str:
    where = _where(path, ev)
    change_type = change["type"]
    old = change.get("old_value") or "nothing"
    new = change.get("new_value") or "nothing"

    if kind == "test":
        if change_type == "value_change":
            return f"Update test at {where} for {old} → {new}"
        return f"Review test at {where}"

    if kind == "doc":
        if change_type == "value_change":
            return f"Update documentation at {where}: {old} → {new}"
        return f"Update documentation at {where}"

    # code
    if change_type == "value_change":
        if ev.get("literal"):
            return f"Change {old} → {new} at {where}"
        return (f"Review {where}: related to {change['entity']} {change['property']}, "
                f"old value {old} not found directly")
    if change_type == "added":
        return f"Review {where}: new requirement may need changes here"
    if change_type == "removed":
        return f"Review {where}: requirement removed, this code may be obsolete"
    return f"Review {where}: requirement wording changed"


def confidence_of(ev: dict) -> str:
    """How sure we are that this line is really related to the change."""
    matched = len(ev.get("matched", []))
    if ev.get("literal") and matched >= 2:
        return "high"
    if ev.get("literal") or matched >= 3:
        return "medium"
    return "low"


def reason_of(ev: dict) -> str:
    parts = []
    if ev.get("literal"):
        parts.append(f"old value found: {ev['literal']}")
    if ev.get("matched"):
        parts.append("matched keywords: " + ", ".join(ev["matched"]))
    return "; ".join(parts) or "weak match"


def build_action_plan(results: list[dict]) -> list[dict]:
    """results = analyze_impact() ka output."""
    items: list[dict] = []

    for index, result in enumerate(results):
        change = result["change"]

        if not result["files"]:
            label = f"{change['entity']} {change['property']}".strip()
            items.append({
                "kind": "manual",
                "text": f"No matching code found for '{label}': insufficient evidence, check manually",
                "path": None, "line": None, "function": None, "evidence": None,
                "change_index": index, "key": None, "confidence": None, "reason": None,
            })
            continue

        # code -> test -> doc (har group me score ka order wahi rehta hai)
        for f in sorted(result["files"], key=lambda f: KIND_ORDER.get(f["kind"], 9)):
            ev = f["evidence"][0]
            text = describe(change, f["kind"], f["path"], ev)
            extra = len(f["evidence"]) - 1
            if extra > 0:
                text += f" (+{extra} more related line(s) in this file)"
            items.append({
                "kind": f["kind"],
                "text": text,
                "path": f["path"],
                "line": ev["line"],
                "function": ev.get("function"),
                "evidence": ev["text"],
                "change_index": index,
                "key": f"{index}:{f['path']}:{ev['line']}",
                "confidence": confidence_of(ev),
                "reason": reason_of(ev),
            })

    test_paths = sorted({i["path"] for i in items if i["kind"] == "test"})
    if test_paths:
        items.append({
            "kind": "run",
            "text": "Run tests: " + ", ".join(test_paths),
            "path": None, "line": None, "function": None, "evidence": None,
            "change_index": None, "key": None, "confidence": None, "reason": None,
        })

    for number, item in enumerate(items, 1):
        item["order"] = number
    return items