"""Markdown report for one saved analysis."""


def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def build_markdown(project_name: str, created_at: str, result: dict) -> str:
    changes = result["changes"]
    plan = result["action_plan"]

    lines = [f"# DriftAI report: {project_name}", "", f"Generated: {created_at}", ""]

    risk = result.get("risk")
    if risk:
        lines += [f"**Risk: {risk['level'].upper()} ({risk['score']}/100)**", ""]
        lines += [f"- {reason}" for reason in risk["reasons"]]
        lines.append("")

    lines += ["## Requirement changes", ""]
    if not changes:
        lines.append("No requirement changes found.")
    else:
        lines += ["| Type | Entity | Property | Old | New |", "|---|---|---|---|---|"]
        for item in changes:
            c = item["change"]
            old = c.get("old_value") or c.get("old_sentence") or "-"
            new = c.get("new_value") or c.get("new_sentence") or "-"
            lines.append(
                f"| {_cell(c['type'])} | {_cell(c['entity'])} | {_cell(c['property'])} "
                f"| {_cell(old)} | {_cell(new)} |"
            )

    lines += ["", "## Action plan", ""]
    if not plan:
        lines.append("No actions needed.")
    for step in plan:
        text = step["text"]
        if step.get("confidence"):
            text += f" (confidence: {step['confidence']})"
        lines.append(f"- [ ] {text}")
        if step.get("reason"):
            lines.append(f"  - Why: {step['reason']}")
        if step.get("evidence"):
            lines.append(f"  - Evidence: `{step['evidence']}`")

    lines += ["", "## Affected files", ""]
    found_any = False
    for item in changes:
        if not item["files"]:
            continue
        found_any = True
        c = item["change"]
        lines += [f"### {c['entity']} · {c['property']}", ""]
        for f in item["files"]:
            lines.append(f"- `{f['path']}` ({f['kind']}, score {f['score']})")
            for e in f["evidence"]:
                where = f"line {e['line']}"
                if e.get("function"):
                    where += f" in {e['function']}()"
                lines.append(f"  - {where}: `{e['text']}`")
        lines.append("")
    if not found_any:
        lines.append("No matching files found.")

    return "\n".join(lines).rstrip() + "\n"