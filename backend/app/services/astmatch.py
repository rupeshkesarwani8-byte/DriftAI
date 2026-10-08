"""Function-level matching (Build 3, improved in Build 7).

Splits code files into "units" (functions, methods, top-level constants) with
Python's `ast` module, then ranks those units against a requirement change.

Signals used for ranking:
  * words in the function/constant NAME          (strong)
  * words in docstring, comments, identifiers    (medium; docstring/comments count double)
  * the old literal value (e.g. 600 for 10 min)  (strong)
  * module constants the function uses           (so send_otp() is linked to OTP_EXPIRY_SECONDS)
  * a small synonym table (token ~ otp, retry ~ attempt ...)
  * rare words count more than common ones       (Build 7)
  * bonus when one function explains every word of the requirement (Build 7)

Non-Python files (js/ts/jsx/tsx) use an approximate regex splitter.
"""
from __future__ import annotations

import ast
import io
import math
import re
import tokenize
from dataclasses import dataclass, field

# ----------------------------------------------------------------- words ----
STOP = {
    "the", "a", "an", "is", "are", "be", "to", "of", "in", "on", "for", "and", "or",
    "must", "should", "will", "can", "may", "with", "by", "at", "from", "after", "before",
    "all", "any", "each", "per", "it", "its", "this", "that", "user", "users", "self",
    "none", "true", "false", "return", "get", "set", "new", "old", "value", "def",
}

# canonical stem -> group name. Words in one group are treated as the same idea.
SYNONYM_GROUPS = [
    {"otp", "token", "pin", "passc"},
    {"login", "signi", "authe", "auth", "logon"},
    {"passw", "passwd", "crede", "secre"},
    {"expir", "timeo", "ttl", "lifet"},
    {"attem", "retry", "retri", "tries", "try", "tri"},
    {"payme", "pay", "charg", "billi"},
    {"refun", "retur", "reimb"},
    {"email", "mail"},
    {"phone", "mobil", "sms"},
    {"limit", "cap", "quota", "throt"},
    {"disco", "coupo", "promo", "offer"},
]
_SYN = {}
for _i, _g in enumerate(SYNONYM_GROUPS):
    for _w in _g:
        _SYN[_w] = f"syn{_i}"

UNIT_SECONDS = {"second": 1, "seconds": 1, "sec": 1, "secs": 1, "s": 1,
                "minute": 60, "minutes": 60, "min": 60, "mins": 60,
                "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600, "h": 3600,
                "day": 86400, "days": 86400}


def split_identifier(name: str) -> list[str]:
    """snake_case / camelCase / UPPER_CASE -> lower-case words."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return [w.lower() for w in re.split(r"[^A-Za-z0-9]+", name) if w]


def stem(word: str) -> str:
    """First 5 letters; a final 'y' becomes 'i' so proxy ~ proxies, retry ~ retries, query ~ queries."""
    s = word.lower()[:5]
    return s[:-1] + "i" if len(s) >= 3 and s.endswith("y") else s


def words_to_stems(words, use_synonyms: bool = True) -> set[str]:
    out = set()
    for w in words:
        w = w.lower()
        if len(w) < 3 or w in STOP or w.isdigit():
            continue
        s = stem(w)
        out.add(_SYN.get(s, s) if use_synonyms else s)
    return out


def text_to_stems(text: str, use_synonyms: bool = True) -> set[str]:
    parts: list[str] = []
    for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text or ""):
        parts.extend(split_identifier(tok))
    return words_to_stems(parts, use_synonyms)


# ----------------------------------------------------------------- units ----
@dataclass
class Unit:
    path: str
    name: str
    qualname: str
    kind: str                 # function | method | constant
    start: int
    end: int
    source: str
    name_words: list[str] = field(default_factory=list)
    context_text: str = ""    # docstring + comments + identifiers + strings
    numbers: set[float] = field(default_factory=set)
    used_constants: list[str] = field(default_factory=list)
    literals: set[str] = field(default_factory=set)   # lower-case True/False/None/short text values
    doc_text: str = ""        # docstring + comments only (Build 7: counts more than plain identifiers)


def _fold(n: ast.AST) -> float | None:
    """Evaluate a constant number or a simple constant expression like 10 * 1024."""
    if isinstance(n, ast.Constant):
        v = n.value
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        return None
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
        v = _fold(n.operand)
        if v is None:
            return None
        return -v if isinstance(n.op, ast.USub) else v
    if isinstance(n, ast.BinOp):
        a, b = _fold(n.left), _fold(n.right)
        if a is None or b is None:
            return None
        try:
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            if isinstance(n.op, ast.FloorDiv):
                return float(a // b)
            if isinstance(n.op, ast.Pow) and abs(b) <= 20:
                return float(a ** b)
        except (ZeroDivisionError, OverflowError, ValueError):
            return None
    return None


def _numbers_in(node: ast.AST) -> set[float]:
    """All numbers under a node. 10 * 1024 counts as 10240 only (not as 10 and 1024)."""
    found: set[float] = set()

    def visit(n: ast.AST) -> None:
        v = _fold(n)
        if v is not None:
            found.add(v)
            return
        for child in ast.iter_child_nodes(n):
            visit(child)

    visit(node)
    return found


def _literal_of(node: ast.AST) -> str | None:
    """Lower-case text of a simple non-number constant: True, False, None or a short string."""
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None or isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, str) and 0 < len(v.strip()) <= 60:
            return v.strip().lower()
    return None


def _comments_by_line(source: str) -> dict[int, str]:
    out: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                out[tok.start[0]] = tok.string.lstrip("# ")
    except (tokenize.TokenError, IndentationError):
        pass
    return out


def index_python(path: str, source: str) -> list[Unit]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    lines = source.splitlines()
    comments = _comments_by_line(source)
    units: list[Unit] = []

    # 1) module-level constants (e.g. OTP_EXPIRY_SECONDS = 600)
    constants: dict[str, float] = {}
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name) and value is not None:
                nums = _numbers_in(value)
                lit = None if nums else _literal_of(value)
                if not nums and lit is None:   # keep numbers, True/False/None and short text values
                    continue
                end = getattr(node, "end_lineno", node.lineno)
                tail = comments.get(node.lineno, "")
                units.append(Unit(
                    path=path, name=t.id, qualname=t.id, kind="constant",
                    start=node.lineno, end=end,
                    source="\n".join(lines[node.lineno - 1:end]),
                    name_words=split_identifier(t.id),
                    context_text=tail, doc_text=tail, numbers=nums,
                    literals={lit} if lit is not None else set(),
                ))
                if len(nums) == 1:
                    constants[t.id] = next(iter(nums))

    # 2) functions and methods
    def visit(node: ast.AST, prefix: str, in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.", True)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if any((isinstance(d, ast.Name) and d.id == "overload")
                       or (isinstance(d, ast.Attribute) and d.attr == "overload")
                       for d in child.decorator_list):
                    continue          # typing.overload stubs are not real code
                end = getattr(child, "end_lineno", child.lineno)
                doc = ast.get_docstring(child) or ""
                idents: list[str] = [a.arg for a in child.args.args]
                strings: list[str] = []
                used: list[str] = []
                for n in ast.walk(child):
                    if isinstance(n, ast.Name):
                        idents.append(n.id)
                        if n.id in constants and n.id not in used:
                            used.append(n.id)
                    elif isinstance(n, ast.Attribute):
                        idents.append(n.attr)
                    elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                        strings.append(n.value[:200])
                cmt = " ".join(comments[i] for i in range(child.lineno, end + 1)
                               if i in comments)
                nums = _numbers_in(child)
                for c in used:
                    nums.add(constants[c])
                units.append(Unit(
                    path=path, name=child.name, qualname=f"{prefix}{child.name}",
                    kind="method" if in_class else "function",
                    start=child.lineno, end=end,
                    source="\n".join(lines[child.lineno - 1:end]),
                    name_words=split_identifier(child.name),
                    context_text=" ".join([doc, cmt, " ".join(idents), " ".join(strings)]),
                    doc_text=f"{doc} {cmt}",
                    numbers=nums, used_constants=used,
                ))
                visit(child, f"{prefix}{child.name}.", False)  # nested defs
            else:
                visit(child, prefix, in_class)

    visit(tree, "", False)
    return units


_JS_DEF = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("
    r"|^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)


def index_js(path: str, source: str) -> list[Unit]:
    """Approximate: a unit runs from one definition to the line before the next."""
    lines = source.splitlines()
    starts = []
    for i, line in enumerate(lines, 1):
        m = _JS_DEF.match(line)
        if m:
            starts.append((i, m.group(1) or m.group(2)))
    units = []
    for k, (ln, name) in enumerate(starts):
        end = (starts[k + 1][0] - 1) if k + 1 < len(starts) else len(lines)
        body = "\n".join(lines[ln - 1:end])
        nums = {float(x) for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", body)}
        units.append(Unit(path=path, name=name, qualname=name, kind="function",
                          start=ln, end=end, source=body,
                          name_words=split_identifier(name),
                          context_text=body, numbers=nums))
    return units


def index_file(path: str, source: str) -> list[Unit]:
    p = path.lower()
    if p.endswith(".py"):
        return index_python(path, source)
    if p.endswith((".js", ".jsx", ".ts", ".tsx")):
        return index_js(path, source)
    return []


# --------------------------------------------------------------- quantity ----
_QTY = re.compile(r"(\d+(?:\.\d+)?)\s*([A-Za-z%]+)?")


def literal_numbers(value_text: str) -> tuple[set[float], list[str]]:
    """'10 minutes' -> ({10.0, 600.0}, ['10 minutes', ...]) so 600 is found too."""
    nums: set[float] = set()
    notes: list[str] = []
    for m in _QTY.finditer(str(value_text or "")):
        n = float(m.group(1))
        unit = (m.group(2) or "").lower()
        nums.add(n)
        if unit in UNIT_SECONDS:
            secs = n * UNIT_SECONDS[unit]
            nums.add(secs)
            notes.append(f"{m.group(1)} {unit} = {int(secs) if secs == int(secs) else secs} seconds")
    return nums, notes


def literal_words(value_text: str) -> set[str]:
    """'False' -> {'false'};  '"utf-8"' -> {'utf-8'};  used to match True/False/None/text constants."""
    text = str(value_text or "").strip().strip("\"'`").lower()
    if not text or len(text) > 60 or re.fullmatch(r"[\d\s.,]+[a-z%]*", text):
        return set()                       # numbers are handled by literal_numbers
    return {text}


# --------------------------------------------------------------- scoring ----
@dataclass
class Match:
    unit: Unit
    score: float
    confidence: str
    reasons: list[str]


def word_weights(units: list[Unit], query: set[str], use_synonyms: bool = True) -> dict[str, float]:
    """Build 7: rare words count more. A word found in many units ('request') says little;
    a word found in few units ('proxy') points to the right place. Range 0.6 .. 1.4."""
    n = max(len(units), 1)
    df = {q: 0 for q in query}
    for u in units:
        seen = words_to_stems(u.name_words, use_synonyms) | text_to_stems(u.context_text, use_synonyms)
        for q in query & seen:
            df[q] += 1
    return {q: max(0.6, min(1.4, 0.6 + math.log((n + 1) / (df[q] + 1)) / 4)) for q in query}


def score_unit(unit: Unit, query: set[str], literal_set: set[float], notes: list[str],
               use_literals: bool = True, use_synonyms: bool = True,
               use_constants: bool = True, word_literals: set[str] | None = None,
               weights: dict[str, float] | None = None) -> tuple[float, list[str]]:
    score, reasons = 0.0, []
    w = (lambda q: weights.get(q, 1.0)) if weights else (lambda q: 1.0)
    name_stems = words_to_stems(unit.name_words, use_synonyms)
    ctx_stems = text_to_stems(unit.context_text, use_synonyms)
    doc_stems = text_to_stems(unit.doc_text, use_synonyms)

    name_hit = query & name_stems
    if name_hit:
        score += sum(3.0 * w(q) for q in name_hit)
        reasons.append("name matches: " + ", ".join(sorted(unit.name_words)[:4]))
    # compound identifiers such as DEFAULT_POOLSIZE: query word "pool" starts the name word "poolsize"
    compound = set()
    for q in query - name_hit:
        if len(q) >= 4 and not q.startswith("syn"):
            if any(x.startswith(q) and len(x) > len(q) for x in (y.lower() for y in unit.name_words)):
                compound.add(q)
    if compound:
        score += sum(2.0 * w(q) for q in compound)
        reasons.append("name contains: " + ", ".join(sorted(compound)))
    name_hit = name_hit | compound
    ctx_hit = (query & ctx_stems) - name_hit
    if ctx_hit:
        doc_hit = ctx_hit & doc_stems
        score += sum((2.0 if q in doc_hit else 1.0) * w(q) for q in ctx_hit)
        reasons.append(f"{len(ctx_hit)} related word(s) in docstring/comments/identifiers")

    covered = name_hit | ctx_hit
    if len(query) >= 2 and covered >= query and (name_hit or doc_stems & query):
        score += 2.0                       # every word of the requirement is explained by this function
        reasons.append("covers all words of the requirement")
        if query <= (doc_stems | name_hit):
            score += 1.0                   # ... and the docstring/comments (not just identifiers) say so

    if use_literals and literal_set and (unit.numbers & literal_set):
        # numbers alone are weak: only count them if there is some word evidence too
        hit = sorted(unit.numbers & literal_set)
        weight = 4.0 if (name_hit or ctx_hit) else 1.0
        if unit.kind == "constant" and weight == 4.0:
            weight += 1.5                  # a constant that IS the old value is the source of truth
        score += weight
        shown = ", ".join(str(int(h)) if h == int(h) else str(h) for h in hit)
        reasons.append(f"contains old value: {shown}" + (f" ({notes[0]})" if notes else ""))

    if use_literals and word_literals and (unit.literals & word_literals) and (name_hit or ctx_hit):
        # False / None / "text" values count only together with word evidence (they are too common alone)
        score += 5.5 if unit.kind == "constant" else 4.0
        reasons.append("contains old value: " + ", ".join(sorted(unit.literals & word_literals)))

    if use_constants and unit.used_constants and (name_hit or ctx_hit or score):
        reasons.append("uses constant: " + ", ".join(unit.used_constants))
    return score, reasons


STRONG_SCORE = 4.0     # at or above this a match is shown as a real suggestion (medium/high)


def confidence_of(score: float) -> str:
    return "high" if score >= 8 else "medium" if score >= STRONG_SCORE else "low"


def rank_units(units: list[Unit], entity: str, prop: str, old_value: str,
               top_k: int = 5, min_score: float = 0.0, query_text: str = "", **flags) -> list[Match]:
    use_syn = flags.get("use_synonyms", True)
    use_meaning = flags.pop("use_meaning", True)
    query = text_to_stems(f"{entity} {prop}", use_syn)
    literal_set, notes = literal_numbers(old_value)
    word_lits = literal_words(old_value)
    sem = None
    if use_meaning and query_text.strip():
        from app.services.embed import semantic_scores   # optional: None when no model is installed
        sem = semantic_scores(units, f"{entity} {prop}. {query_text}", flags.pop("embedder", None))
    flags.pop("embedder", None)
    matches: list[Match] = []
    weights = word_weights(units, query, use_syn) if flags.get("use_weights", True) else None
    flags = {k: v for k, v in flags.items() if k != "use_weights"}
    for i, u in enumerate(units):
        s, why = score_unit(u, query, literal_set, notes, word_literals=word_lits, weights=weights, **flags)
        if sem is not None and sem[i][0] > 0:
            s += sem[i][0]
            why = why + [f"similar meaning to the requirement (similarity {sem[i][1]:.2f})"]
        if s > 0 and s >= min_score:
            matches.append(Match(u, round(s, 1), confidence_of(s), why))
    matches.sort(key=lambda m: (-m.score, m.unit.path, m.unit.start))
    return matches[:top_k]


def build_index(files: list[tuple[str, str]]) -> list[Unit]:
    units: list[Unit] = []
    for path, content in files:
        units.extend(index_file(path, content or ""))
    return units