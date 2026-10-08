"""Build 10: meaning-based matching. Uses a tiny fake model, so no download is needed."""
import pytest

from app.services import embed
from app.services.astmatch import build_index, rank_units

CONCEPTS = [
    {"remove", "removed", "drop", "strip", "delete"},
    {"authorization", "credentials", "auth", "password"},
    {"header", "headers"},
]


class FakeModel:
    """One number per concept: texts that use words of the same concept get similar vectors."""
    def encode(self, texts):
        out = []
        for t in texts:
            words = set(t.lower().replace("_", " ").replace(".", " ").split())
            out.append([float(len(words & c)) for c in CONCEPTS] + [0.01])
        return out


@pytest.fixture(autouse=True)
def reset():
    embed.set_embedder(None)
    yield
    embed.set_embedder(None)


def _units():
    src = "".join(f"def helper_{n}(x):\n    return x\n\n" for n in ("alpha", "beta", "gamma", "delta", "kappa", "omega", "sigma", "theta"))
    src += "def drop_credentials(x):\n    return x\n"
    return build_index([("m.py", src)])


def test_without_a_model_nothing_changes():
    units = _units()
    top = rank_units(units, "authorization header", "removed", "x", query_text="Authorization header is removed")
    assert top == []                         # no shared words, no model: nothing is found (and nothing crashes)


def test_meaning_finds_a_function_with_different_words():
    units = _units()
    embed.set_embedder(FakeModel())
    top = rank_units(units, "authorization header", "removed", "x", query_text="Authorization header is removed")
    assert top and top[0].unit.qualname == "drop_credentials"
    assert any("similar meaning" in r for r in top[0].reasons)


def test_meaning_can_be_switched_off_per_call():
    units = _units()
    embed.set_embedder(FakeModel())
    top = rank_units(units, "authorization header", "removed", "x",
                     query_text="Authorization header is removed", use_meaning=False)
    assert top == []


def test_bonus_is_capped_so_meaning_alone_is_not_high_confidence():
    units = _units()
    embed.set_embedder(FakeModel())
    top = rank_units(units, "authorization header", "removed", "x", query_text="Authorization header is removed")
    assert top[0].score <= 3.5 and top[0].confidence == "low"


def test_env_switch_turns_the_model_off(monkeypatch):
    monkeypatch.setenv("DRIFTAI_EMBEDDINGS", "off")
    embed._embedder, embed._tried = None, False
    assert embed.get_embedder() is None