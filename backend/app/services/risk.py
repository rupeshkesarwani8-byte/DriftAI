"""Risk score for one analysis (how serious could this change be?).

This is different from confidence (how sure we are about a match).
"""
from .drift import extract_quantities, key_words

SENSITIVE_PREFIXES = (
    "otp", "passw", "auth", "login", "token", "paym", "refun", "secur",
    "encry", "permi", "price", "tax", "invoi", "creden", "sessi",
)


def sensitive_words(results: list[dict]) -> list[str]:
    found: set[str] = set()
    for item in results:
        change = item["change"]
        for sentence in (change.get("old_sentence"), change.get("new_sentence")):
            if not sentence:
                continue
            for word in key_words(sentence, extract_quantities(sentence)):
                if word.startswith(SENSITIVE_PREFIXES):
                    found.add(word)
    return sorted(found)


def compute_risk(results: list[dict], plan: list[dict]) -> dict:
    if not results:
        return {"score": 0, "level": "low", "reasons": ["No requirement changes found"]}

    words = sensitive_words(results)
    score = 70 if words else 30
    reasons = [
        f"Touches a sensitive area: {', '.join(words)}" if words else "No sensitive keywords found"
    ]

    if any(item["change"]["type"] == "removed" for item in results):
        score += 10
        reasons.append("A requirement was removed")

    files = {i["path"] for i in plan if i.get("path")}
    spread = min(25, 5 * len(files))
    if spread:
        score += spread
        reasons.append(f"{len(files)} file(s) affected")

    kinds = {i["kind"] for i in plan}
    if "code" in kinds and "test" not in kinds:
        score += 10
        reasons.append("No test is linked to the affected code")

    manual = sum(1 for i in plan if i["kind"] == "manual")
    if manual:
        reasons.append(f"{manual} change(s) have no matching code (insufficient evidence)")

    score = min(100, score)
    level = "high" if score >= 70 else "medium" if score >= 45 else "low"
    return {"score": score, "level": level, "reasons": reasons}