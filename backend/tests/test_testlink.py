from app.services.astmatch import build_index
from app.services.fnimpact import functions_for_changes
from app.services.testlink import suggest_tests

SHOP = (
    "MAX_DISCOUNT_PERCENT = 20\n\n"
    "def apply_discount(price, percent):\n"
    "    percent = min(percent, MAX_DISCOUNT_PERCENT)\n"
    "    return price - price * percent / 100\n"
)
TESTS = (
    "from shop import apply_discount\n\n"
    "def test_big_discount_is_capped():\n"
    "    assert apply_discount(1000, 50) == 800\n\n"
    "def test_unrelated():\n"
    "    assert 1 + 1 == 2\n"
)


def _item(matches):
    return {"entity": "discount", "property": "%", "old_value": "20%", "new_value": "30%",
            "matches": matches, "weak_matches": []}


def _m(path, qualname, start=1, end=2):
    return {"path": path, "qualname": qualname, "start_line": start, "end_line": end, "confidence": "high"}


def test_test_that_uses_the_matched_function_is_listed():
    units = build_index([("shop.py", SHOP), ("tests/test_shop.py", TESTS)])
    out = suggest_tests(units, [_item([_m("shop.py", "apply_discount")])])
    names = [t["qualname"] for t in out[0]["tests"]]
    assert names == ["test_big_discount_is_capped"]
    assert out[0]["tests"][0]["pytest"] == "tests/test_shop.py::test_big_discount_is_capped"
    assert out[0]["tests"][0]["reason"] == "uses apply_discount"


def test_direct_test_match_comes_first_and_is_not_repeated():
    units = build_index([("shop.py", SHOP), ("tests/test_shop.py", TESTS)])
    items = [_item([_m("tests/test_shop.py", "test_big_discount_is_capped"), _m("shop.py", "apply_discount")])]
    tests = suggest_tests(units, items)[0]["tests"]
    assert [t["qualname"] for t in tests] == ["test_big_discount_is_capped"]
    assert tests[0]["reason"] == "matches the requirement directly"


def test_missing_tests_are_reported_honestly():
    units = build_index([("shop.py", SHOP)])
    out = suggest_tests(units, [_item([_m("shop.py", "apply_discount")])])
    assert out[0]["tests"] == [] and "No test was found" in out[0]["note"]


def test_no_match_means_no_suggestion():
    units = build_index([("shop.py", SHOP)])
    out = suggest_tests(units, [_item([])])
    assert out[0]["tests"] == [] and "No strong match" in out[0]["note"]


def test_end_to_end_with_saved_analysis_shape():
    units = build_index([("shop.py", SHOP), ("tests/test_shop.py", TESTS)])
    saved = [{"change": {"type": "value_change", "entity": "discount", "property": "%",
                         "old_value": "20%", "new_value": "30%",
                         "old_sentence": "The maximum discount is 20 percent.",
                         "new_sentence": "The maximum discount is 30 percent."}, "files": []}]
    out = suggest_tests(units, functions_for_changes(units, saved))
    assert any(t["qualname"] == "test_big_discount_is_capped" for t in out[0]["tests"])