"""Meaning-based matching (Build 10).

The word matcher in astmatch.py only sees shared WORDS. An embedding model turns a text into a list of numbers
that captures its MEANING, so "strip the authorization header on redirect" can find rebuild_auth even if the
words differ. DriftAI uses it as an extra signal on top of the word score, never instead of it.

Safe by design: if no model can be loaded (package not installed, no internet for the first download, or
DRIFTAI_EMBEDDINGS=off) everything silently falls back to the word matcher.

Install ONE of these (fastembed is lighter, sentence-transformers is the common one):
    pip install fastembed
    pip install sentence-transformers
"""
from __future__ import annotations

import hashlib
import os
import threading
from typing import Protocol

MODEL_NAME = "all-MiniLM-L6-v2"
_lock = threading.Lock()
_embedder = None
_tried = False
_cache: dict[tuple, list[float]] = {}


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class _FastEmbed:
    def __init__(self):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(f"sentence-transformers/{MODEL_NAME}")

    def encode(self, texts):
        return [list(map(float, v)) for v in self.model.embed(texts)]


class _SentenceTransformers:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(MODEL_NAME)

    def encode(self, texts):
        return [list(map(float, v)) for v in self.model.encode(texts, normalize_embeddings=True)]


def set_embedder(e) -> None:
    """Use a given embedder (tests and benchmarks). Pass None to switch meaning-matching off."""
    global _embedder, _tried
    with _lock:
        _embedder, _tried = e, True
        _cache.clear()


def get_embedder():
    """The embedder, loaded once. None when unavailable."""
    global _embedder, _tried
    if _tried:
        return _embedder
    with _lock:
        if _tried:
            return _embedder
        _tried = True
        if os.environ.get("DRIFTAI_EMBEDDINGS", "").lower() in {"off", "0", "false", "no"}:
            return None
        for cls in (_FastEmbed, _SentenceTransformers):
            try:
                _embedder = cls()
                break
            except Exception:   # not installed, no network for the first download, unsupported Python ...
                continue
        return _embedder


def unit_text(u) -> str:
    """What the model reads about a function: its name as words plus the start of its docstring/comments."""
    return (" ".join(u.name_words) + ". " + (u.doc_text or "").strip())[:400]


def _norm(v):
    s = sum(x * x for x in v) ** 0.5 or 1.0
    return [x / s for x in v]


def _vectors(embedder, texts: list[str]) -> list[list[float]]:
    out: list[list[float] | None] = []
    missing: list[tuple[int, str, tuple]] = []
    for i, t in enumerate(texts):
        key = (hashlib.sha1(t.encode("utf-8", "ignore")).hexdigest(),)
        hit = _cache.get(key)
        out.append(hit)
        if hit is None:
            missing.append((i, t, key))
    if missing:
        vecs = embedder.encode([t for _, t, _ in missing])
        for (i, _, key), v in zip(missing, vecs):
            nv = _norm(list(v))
            _cache[key] = nv
            out[i] = nv
    return out  # type: ignore[return-value]


def semantic_scores(units, query_text: str, embedder=None) -> list[tuple[float, float]] | None:
    """For each unit: (bonus, similarity). None when meaning-matching is unavailable.

    The bonus uses the unit's z-score inside THIS query (how far above the average unit it is), so it does not
    depend on which model is used. Only clearly-above-average units get a bonus, at most 3.5 points.
    """
    emb = embedder or get_embedder()
    if emb is None or not units or not query_text.strip():
        return None
    try:
        vecs = _vectors(emb, [unit_text(u) for u in units])
        q = _norm(list(emb.encode([query_text])[0]))
    except Exception:
        return None
    sims = [sum(a * b for a, b in zip(q, v)) for v in vecs]
    n = len(sims)
    mean = sum(sims) / n
    std = (sum((s - mean) ** 2 for s in sims) / n) ** 0.5 or 1.0
    out = []
    for s in sims:
        z = (s - mean) / std
        out.append((min(3.5, 1.2 * (z - 0.8)) if z > 0.8 else 0.0, s))
    return out                                                                                                                                                                                                          