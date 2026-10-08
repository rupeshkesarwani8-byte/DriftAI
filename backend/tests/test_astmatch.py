from app.services.astmatch import (
    build_index, index_python, literal_numbers, rank_units, split_identifier,
)

SRC = '''
OTP_EXPIRY_SECONDS = 600  # OTP 10 minute me expire hota hai
_store = {}

def send_otp(phone):
    """Create an OTP."""
    return "123456"

def verify_otp(code, age):
    if age > OTP_EXPIRY_SECONDS:
        return False
    return True

class Orders:
    def cancel_order(self, hours):
        return hours < 24
'''


def test_split_identifier():
    assert split_identifier("OTP_EXPIRY_SECONDS") == ["otp", "expiry", "seconds"]
    assert split_identifier("verifyOtpCode") == ["verify", "otp", "code"]


def test_index_finds_functions_methods_and_constants():
    units = index_python("auth.py", SRC)
    names = {u.qualname: u for u in units}
    assert "send_otp" in names and "verify_otp" in names
    assert names["Orders.cancel_order"].kind == "method"
    assert names["OTP_EXPIRY_SECONDS"].kind == "constant"
    assert "_store" not in names                      # no number -> not a unit
    assert names["verify_otp"].used_constants == ["OTP_EXPIRY_SECONDS"]
    assert names["verify_otp"].start < names["verify_otp"].end


def test_unit_conversion():
    nums, notes = literal_numbers("10 minutes")
    assert 10.0 in nums and 600.0 in nums
    assert "600 seconds" in notes[0]


def test_rank_puts_constant_and_user_first():
    units = build_index([("auth.py", SRC)])
    top = rank_units(units, "OTP", "expires", "10 minutes", top_k=3)
    found = [m.unit.qualname for m in top]
    assert "OTP_EXPIRY_SECONDS" in found[:2]
    assert "verify_otp" in found
    assert top[0].confidence in {"high", "medium"}
    assert any("old value" in r for r in top[0].reasons)


def test_unrelated_requirement_gets_no_high_confidence():
    units = build_index([("auth.py", SRC)])
    top = rank_units(units, "delivery fee", "waived above", "999 rupees")
    assert all(m.confidence != "high" for m in top)


def test_bad_syntax_is_skipped_not_crashed():
    assert index_python("broken.py", "def (:\n") == []


def test_overload_stubs_are_skipped():
    src = (
        "from typing import overload\n"
        "@overload\n"
        "def f(a: int) -> int: ...\n"
        "@overload\n"
        "def f(a: str) -> str: ...\n"
        "def f(a):\n"
        "    return a\n"
    )
    units = index_python("x.py", src)
    assert [u.qualname for u in units] == ["f"]
    assert units[0].start == 6


def test_constant_expression_is_folded():
    src = "CONTENT_CHUNK_SIZE = 10 * 1024\nITER = 512\n"
    units = {u.qualname: u for u in index_python("m.py", src)}
    assert units["CONTENT_CHUNK_SIZE"].numbers == {10240.0}      # not {10, 1024}
    assert units["ITER"].numbers == {512.0}


def test_compound_identifier_matches_query_word():
    src = "DEFAULT_POOLSIZE = 10\nOTHER_VALUE = 10\n"
    units = build_index([("a.py", src)])
    top = rank_units(units, "connection pool", "size", "10")
    assert top[0].unit.qualname == "DEFAULT_POOLSIZE"
    assert any("name contains" in r for r in top[0].reasons)


def test_min_score_hides_weak_matches():
    units = build_index([("a.py", "SESSION_TIMEOUT = 30\n")])
    weak = rank_units(units, "customers", "signed out", "30 minutes")        # number only
    assert weak and weak[0].score < 4
    assert rank_units(units, "customers", "signed out", "30 minutes", min_score=4) == []


def test_bool_none_and_text_constants_are_indexed():
    src = 'POOLBLOCK = False\nPOOL_TIMEOUT = None\nDEFAULT_CHARSET = "utf-8"\nPLAIN = some_call()\n'
    units = {u.qualname: u for u in index_python("m.py", src)}
    assert units["POOLBLOCK"].literals == {"false"}
    assert units["POOL_TIMEOUT"].literals == {"none"}
    assert units["DEFAULT_CHARSET"].literals == {"utf-8"}
    assert "PLAIN" not in units                       # a function call is not a simple value


def test_false_value_needs_word_evidence():
    units = build_index([("a.py", "POOLBLOCK = False\nOTHER_FLAG = False\n")])
    top = rank_units(units, "connection pool", "block", "False")
    assert top[0].unit.qualname == "POOLBLOCK"
    assert any("contains old value: false" in r for r in top[0].reasons)
    # a bare 'False' with no related words must not match every False constant
    assert rank_units(units, "customers", "greeting", "False") == []


def test_plural_and_singular_share_a_stem():
    from app.services.astmatch import stem
    assert stem("proxy") == stem("proxies")
    assert stem("retry") == stem("retries")
    assert stem("cookie") == stem("cookies")



def test_rare_word_outweighs_common_word():
    # 'request' is in many unit names, 'proxy' in one: the proxy function must win
    src = (
        "def build_request(a):\n    return a\n"
        "def send_request(a):\n    return a\n"
        "def parse_request(a):\n    return a\n"
        "def rebuild_proxies(a):\n    return a\n"
    )
    units = build_index([("s.py", src)])
    top = rank_units(units, "proxy", "request", "x")
    assert top[0].unit.qualname == "rebuild_proxies"


def test_docstring_words_count_more_than_plain_identifiers():
    src = (
        'def strip_header(auth):\n    """Remove the authorization header when a redirect changes host."""\n    return auth\n'
        "def other(authorization, header, redirect, host):\n    return 1\n"
    )
    units = build_index([("s.py", src)])
    top = rank_units(units, "authorization header", "redirect host", "removed")
    assert top[0].unit.qualname == "strip_header"
    assert any("covers all words" in r for r in top[0].reasons)