"""Requirement drift detection (rule-based MVP).

Old aur new requirement text ko compare karke batata hai kya badla:
entity, property, old value, new value.
"""
import re
from dataclasses import dataclass

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "by", "for", "of", "to", "is", "are",
    "be", "been", "will", "shall", "must", "should", "can", "may", "only",
    "than", "least", "most", "after", "within", "before", "and", "or", "as",
    "with", "from", "that", "this", "it", "its", "every", "each", "per", "up",
    "upto", "get", "has", "have", "max", "maximum", "minimum",
}

UNIT_ALIASES = {
    "sec": "seconds", "secs": "seconds", "second": "seconds", "seconds": "seconds",
    "min": "minutes", "mins": "minutes", "minute": "minutes", "minutes": "minutes",
    "hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
    "day": "days", "days": "days",
    "week": "weeks", "weeks": "weeks",
    "percent": "%", "%": "%",
    "attempt": "attempts", "attempts": "attempts",
    "character": "characters", "characters": "characters",
    "char": "characters", "chars": "characters",
    "digit": "digits", "digits": "digits",
    "time": "times", "times": "times",
    "retry": "retries", "retries": "retries",
    "request": "requests", "requests": "requests",
    "ms": "ms", "millisecond": "ms", "milliseconds": "ms",
    "mb": "mb", "kb": "kb", "gb": "gb",
}
KNOWN_UNITS = set(UNIT_ALIASES.values())

MATCH_THRESHOLD = 0.5  # do sentences ko "same requirement" tab maanna jab itni similarity ho

NUMBER_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(?:\s*(%|[A-Za-z]+))?")
BULLET_RE = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+")


@dataclass
class Quantity:
    value: float
    unit: str
    start: int
    end: int


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for line in text.splitlines():
        line = BULLET_RE.sub("", line).strip()
        if not line:
            continue
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


def normalize(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.lower()).strip(" .!?")


def extract_quantities(sentence: str) -> list[Quantity]:
    found: list[Quantity] = []
    for m in NUMBER_RE.finditer(sentence):
        raw_unit = (m.group(2) or "").lower()
        unit = UNIT_ALIASES.get(raw_unit, raw_unit)
        if unit in KNOWN_UNITS:
            end = m.end()
        else:
            unit = ""
            end = m.end(1)
        found.append(Quantity(float(m.group(1)), unit, m.start(), end))
    return found


def format_value(q: Quantity) -> str:
    num = str(int(q.value)) if q.value.is_integer() else str(q.value)
    if q.unit == "%":
        return num + "%"
    return f"{num} {q.unit}".strip()


def key_words(sentence: str, quantities: list[Quantity]) -> list[str]:
    """Number+unit hata kar bacha hua matlab wale shabd."""
    text = sentence
    for q in sorted(quantities, key=lambda q: q.start, reverse=True):
        text = text[: q.start] + " " + text[q.end:]
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def keyset(sentence: str) -> set[str]:
    return {stem(w) for w in key_words(sentence, extract_quantities(sentence))}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def entity_and_property(sentence: str, q: Quantity) -> tuple[str, str]:
    """Number se pehle ke shabdon se entity aur property andaza lagata hai."""
    left = re.findall(r"[A-Za-z]+", sentence[: q.start])
    words = [w for w in left if w.lower() not in STOP_WORDS]
    if not words:
        return "requirement", q.unit or "value"
    entity = words[0]
    prop = " ".join(words[1:]).lower() or q.unit or "value"
    return entity, prop


def make_change(kind, entity, prop, old_value, new_value, old_s, new_s) -> dict:
    return {
        "type": kind,
        "entity": entity,
        "property": prop,
        "old_value": old_value,
        "new_value": new_value,
        "old_sentence": old_s,
        "new_sentence": new_s,
    }


def first_keyword(sentence: str) -> str:
    words = key_words(sentence, extract_quantities(sentence))
    return words[0] if words else "requirement"


def compare_pair(old_s: str, new_s: str) -> list[dict]:
    old_q, new_q = extract_quantities(old_s), extract_quantities(new_s)
    changes: list[dict] = []

    for i in range(max(len(old_q), len(new_q))):
        o = old_q[i] if i < len(old_q) else None
        n = new_q[i] if i < len(new_q) else None
        if o and n and o.value == n.value and o.unit == n.unit:
            continue
        ref_sentence, ref_q = (old_s, o) if o else (new_s, n)
        entity, prop = entity_and_property(ref_sentence, ref_q)
        changes.append(make_change(
            "value_change", entity, prop,
            format_value(o) if o else None,
            format_value(n) if n else None,
            old_s, new_s,
        ))

    if not changes:
        changes.append(make_change(
            "modified", first_keyword(new_s), "wording", None, None, old_s, new_s
        ))
    return changes


def detect_drift(old_text: str, new_text: str) -> list[dict]:
    old_sents = split_sentences(old_text)
    new_sents = split_sentences(new_text)
    remaining_new = list(range(len(new_sents)))
    unmatched_old: list[int] = []

    # Pass 1: bilkul same sentences = unchanged
    for i, sentence in enumerate(old_sents):
        match = next(
            (j for j in remaining_new if normalize(new_sents[j]) == normalize(sentence)),
            None,
        )
        if match is None:
            unmatched_old.append(i)
        else:
            remaining_new.remove(match)

    # Pass 2: milte-julte sentences jodo aur compare karo
    changes: list[dict] = []
    for i in unmatched_old:
        old_s = old_sents[i]
        old_keys = keyset(old_s)
        best_j, best_score = None, 0.0
        for j in remaining_new:
            score = similarity(old_keys, keyset(new_sents[j]))
            if score > best_score:
                best_j, best_score = j, score
        if best_j is not None and best_score >= MATCH_THRESHOLD:
            remaining_new.remove(best_j)
            changes += compare_pair(old_s, new_sents[best_j])
        else:
            changes.append(make_change(
                "removed", first_keyword(old_s), "requirement", None, None, old_s, None
            ))

    # Jinka jodi nahi mila wo naye requirements hain
    for j in remaining_new:
        changes.append(make_change(
            "added", first_keyword(new_sents[j]), "requirement", None, None, None, new_sents[j]
        ))
    return changes