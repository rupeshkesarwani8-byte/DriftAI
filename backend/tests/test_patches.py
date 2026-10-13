from app.services.astmatch import build_index
from app.services.fnimpact import functions_for_changes
from app.services.patches import suggest_patches

SHOP = (
    "MAX_DISCOUNT_PERCENT = 20\n"
    "FREE_DELIVERY_ABOVE = 500\n\n"
    "def apply_discount(price, percent):\n"
    "    percent = min(percent, MAX_DISCOUNT_PERCENT)\n"
    "    return price - price * percent / 100\n"
)


def _units(src=SHOP, path="shop.py"):
    return build_index([(path, src)])


def _item(old, new, qualnames, path="shop.py"):
    return {"entity": "x", "property": "y", "old_value": old, "new_value": new,
            "matches": [{"path": path, "qualname": q, "confidence": "high"} for q in qualnames],
            "weak_matches": []}


def test_constant_line_is_rewritten():
    out = suggest_patches(_units(), [_item("20%", "30%", ["MAX_DISCOUNT_PERCENT"])])
    e = out[0]["edits"][0]
    assert (e["line"], e["before"], e["after"]) == (1, "MAX_DISCOUNT_PERCENT = 20", "MAX_DISCOUNT_PERCENT = 30")
    assert e["kind"] == "code"


def test_unit_conversion_is_applied():
    units = _units("OTP_SECONDS = 600\n")
    out = suggest_patches(units, [_item("10 minutes", "5 minutes", ["OTP_SECONDS"])])
    e = out[0]["edits"][0]
    assert e["after"] == "OTP_SECONDS = 300" and "seconds" in e["note"]


def test_unit_change_gives_no_edit():
    out = suggest_patches(_units(), [_item("10 minutes", "2 hours", ["MAX_DISCOUNT_PERCENT"])])
    assert out[0]["edits"] == [] and "unit changed" in out[0]["note"]


def test_no_strong_match_gives_no_edit():
    out = suggest_patches(_units(), [_item("20%", "30%", [])])
    assert out[0]["edits"] == [] and "No strong match" in out[0]["note"]


def test_number_not_found_says_so():
    out = suggest_patches(_units(), [_item("99", "98", ["MAX_DISCOUNT_PERCENT"])])
    assert out[0]["edits"] == [] and "not found" in out[0]["note"]


def test_end_to_end_with_saved_analysis_shape():
    units = _units()
    saved = [{"change": {"type": "value_change", "entity": "discount", "property": "%",
                         "old_value": "20%", "new_value": "30%",
                         "old_sentence": "The maximum discount is 20 percent.",
                         "new_sentence": "The maximum discount is 30 percent."}, "files": []}]
    out = suggest_patches(units, functions_for_changes(units, saved))
    assert any(e["after"] == "MAX_DISCOUNT_PERCENT = 30" for e in out[0]["edits"])