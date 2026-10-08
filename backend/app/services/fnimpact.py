"""Glue between the database, the drift changes and the AST matcher (Build 4.5)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import CodeFile
from app.services.astmatch import STRONG_SCORE, Match, rank_units


def get_field(obj, *names, default=""):
    """Read a field from a dict OR an object, trying several possible names."""
    for n in names:
        if isinstance(obj, dict) and obj.get(n) not in (None, ""):
            return obj[n]
        v = getattr(obj, n, None)
        if v not in (None, ""):
            return v
    return default


def file_pairs(db: Session, project_id: int | None) -> list[tuple[str, str]]:
    if project_id is None:
        return []
    rows = db.query(CodeFile).filter(CodeFile.project_id == project_id).all()
    return [(str(get_field(f, "path", "filename", "name")), str(get_field(f, "content", "text", "source")))
            for f in rows]


def match_to_dict(m: Match) -> dict:
    return {
        "path": m.unit.path, "qualname": m.unit.qualname, "kind": m.unit.kind,
        "start_line": m.unit.start, "end_line": m.unit.end, "score": m.score,
        "confidence": m.confidence, "reasons": m.reasons,
        "snippet": "\n".join(m.unit.source.splitlines()[:12]),
    }


def functions_for_changes(units, changes, top_k: int = 5) -> list[dict]:
    """For every change return strong matches (medium/high) and, separately, weak ones."""
    out = []
    for ch in changes:
        entity = str(get_field(ch, "entity"))
        prop = str(get_field(ch, "property", "prop"))
        old_v = str(get_field(ch, "old_value", "old"))
        new_v = str(get_field(ch, "new_value", "new"))
        # the old sentence describes what the existing code does, so it is the text used for meaning-matching
        sentence = str(get_field(ch, "old_sentence", "new_sentence"))
        ranked = rank_units(units, entity, prop, old_v, top_k=top_k * 4, query_text=sentence)
        strong = [m for m in ranked if m.score >= STRONG_SCORE][:top_k]
        weak = [m for m in ranked if m.score < STRONG_SCORE][:top_k]
        out.append({
            "entity": entity, "property": prop, "old_value": old_v, "new_value": new_v,
            "matches": [match_to_dict(m) for m in strong],
            "weak_matches": [match_to_dict(m) for m in weak],
        })
    return out