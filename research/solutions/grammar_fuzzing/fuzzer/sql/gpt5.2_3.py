import os
import re
import json
from typing import Dict, Any


class Solution:
    def solve(self, resources_path: str) -> dict:
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")
        parser_path = os.path.join(resources_path, "sql_engine", "parser.py")
        tokenizer_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
        ast_nodes_path = os.path.join(resources_path, "sql_engine", "ast_nodes.py")

        def _read(p: str) -> str:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

        grammar_text = _read(grammar_path)
        parser_text = _read(parser_path)
        tokenizer_text = _read(tokenizer_path)
        ast_text = _read(ast_nodes_path)

        # Extract some keywords-ish tokens to help template generation.
        def _extract_keywords(*texts: str):
            kws = set()
            for t in texts:
                for m in re.finditer(r"['\"]([A-Z][A-Z0-9_]{1,})['\"]", t):
                    s = m.group(1)
                    if 2 <= len(s) <= 25:
                        kws.add(s)
                for m in re.finditer(r"\b([A-Z][A-Z0-9_]{2,})\b", t):
                    s = m.group(1)
                    if 2 <= len(s) <= 25:
                        kws.add(s)
            # Common SQL keywords for breadth (will be filtered by parser acceptance).
            kws.update([
                "SELECT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET",
                "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
                "CREATE", "TABLE", "DROP", "ALTER", "INDEX", "VIEW", "TRIGGER",
                "DISTINCT", "ALL", "AS", "AND", "OR", "NOT", "NULL", "IS", "IN", "LIKE",
                "BETWEEN", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
                "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "JOIN", "ON", "USING",
                "UNION", "INTERSECT", "EXCEPT", "WITH", "RECURSIVE",
                "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CHECK", "UNIQUE", "DEFAULT",
                "BEGIN", "COMMIT", "ROLLBACK", "TRANSACTION",
            ])
            return sorted(kws)

        extra_keywords = _extract_keywords(parser_text, tokenizer_text, ast_text)

        code = f"""
import re
import time
import random
import string
from typing import List, Dict, Tuple, Optional, Any

GRAMMAR_TEXT = {json.dumps(grammar_text)}
EXTRA_KEYWORDS = {json.dumps(extra_keywords)}

# ---------------- Grammar parsing (EBNF-ish) ----------------

class _Tok:
    __slots__ = ("t", "v")
    def __init__(self, t: str, v: str):
        self.t = t
        self.v = v

def _strip_comments(line: str) -> str:
    # Keep it simple: remove '#' and '//' comments when not inside quotes.
    out = []
    i = 0
    in_s = False
    in_d = False
    while i < len(line):
        c = line[i]
        if c == "'" and not in_d:
            in_s = not in_s
            out.append(c); i += 1; continue
        if c == '"' and not in_s:
            in_d = not in_d
            out.append(c); i += 1; continue
        if not in_s and not in_d:
            if c == '#':
                break
            if c == '/' and i + 1 < len(line) and line[i+1] == '/':
                break
        out.append(c)
        i += 1
    return ''.join(out).strip()

def _tokenize_ebnf(s: str) -> List[_Tok]:
    toks: List[_Tok] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        # separators and operators relevant to grammar
        if s.startswith("::=", i):
            toks.append(_Tok("SEP", "::=")); i += 3; continue
        if s.startswith("->", i):
            toks.append(_Tok("SEP", "->")); i += 2; continue
        if c in "|()[]{}*+?;":
            toks.append(_Tok("P", c)); i += 1; continue
        # angle nonterminal
        if c == "<":
            j = i + 1
            while j < n and s[j] != ">":
                j += 1
            if j < n and s[j] == ">":
                name = s[i+1:j].strip()
                toks.append(_Tok("NT", name))
                i = j + 1
                continue
            # fallthrough if unmatched
        # string literal as terminal
        if c == "'" or c == '"':
            q = c
            j = i + 1
            while j < n:
                if s[j] == q:
                    if j + 1 < n and s[j+1] == q:
                        j += 2
                        continue
                    break
                if s[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                j += 1
            if j < n and s[j] == q:
                lit = s[i:j+1]
                toks.append(_Tok("LIT", lit))
                i = j + 1
                continue
            # unterminated quote: take rest
            toks.append(_Tok("LIT", s[i:]))
            break
        # identifier / terminal token
        if c.isalpha() or c == "_" or c.isdigit():
            j = i + 1
            while j < n and (s[j].isalnum() or s[j] in ("_", "$")):
                j += 1
            toks.append(_Tok("ID", s[i:j]))
            i = j
            continue
        # punctuation tokens are terminals too
        # group common two-char puncts
        if i + 1 < n and s[i:i+2] in ("<=", ">=", "<>", "!=", "==", "||", "&&", "::"):
            toks.append(_Tok("LIT", s[i:i+2])); i += 2; continue
        toks.append(_Tok("LIT", c))
        i += 1
    return toks

# AST node: tuple with tag
# ('lit', str) | ('nt', name) | ('seq', [node...]) | ('alt', [node...]) | ('opt', node) | ('rep', node, minr, maxr)

class _EBNFParser:
    __slots__ = ("toks", "i", "nonterms")
    def __init__(self, toks: List[_Tok], nonterms: set):
        self.toks = toks
        self.i = 0
        self.nonterms = nonterms

    def _peek(self) -> Optional[_Tok]:
        if self.i < len(self.toks):
            return self.toks[self.i]
        return None

    def _eat(self) -> Optional[_Tok]:
        if self.i < len(self.toks):
            t = self.toks[self.i]
            self.i += 1
            return t
        return None

    def parse_expr(self):
        return self._parse_alt()

    def _parse_alt(self):
        seq = self._parse_seq()
        alts = [seq]
        while True:
            p = self._peek()
            if p is None or not (p.t == "P" and p.v == "|"):
                break
            self._eat()  # |
            alts.append(self._parse_seq())
        if len(alts) == 1:
            return alts[0]
        return ("alt", alts)

    def _parse_seq(self):
        parts = []
        while True:
            p = self._peek()
            if p is None:
                break
            if p.t == "P" and p.v in (")", "]", "}", "|", ";"):
                break
            parts.append(self._parse_postfix())
        if not parts:
            return ("seq", [])
        if len(parts) == 1:
            return parts[0]
        return ("seq", parts)

    def _parse_postfix(self):
        atom = self._parse_atom()
        p = self._peek()
        if p is not None and p.t == "P" and p.v in ("?", "*", "+"):
            q = self._eat().v
            if q == "?":
                return ("opt", atom)
            if q == "*":
                return ("rep", atom, 0, 2)
            return ("rep", atom, 1, 3)
        return atom

    def _parse_atom(self):
        p = self._peek()
        if p is None:
            return ("seq", [])
        if p.t == "P" and p.v == "(":
            self._eat()
            e = self._parse_alt()
            if self._peek() is not None and self._peek().t == "P" and self._peek().v == ")":
                self._eat()
            return e
        if p.t == "P" and p.v == "[":
            self._eat()
            e = self._parse_alt()
            if self._peek() is not None and self._peek().t == "P" and self._peek().v == "]":
                self._eat()
            return ("opt", e)
        if p.t == "P" and p.v == "{":
            self._eat()
            e = self._parse_alt()
            if self._peek() is not None and self._peek().t == "P" and self._peek().v == "}":
                self._eat()
            return ("rep", e, 0, 3)
        if p.t == "NT":
            self._eat()
            return ("nt", p.v)
        t = self._eat()
        if t.t == "LIT":
            return ("lit", t.v)
        if t.t == "ID":
            # treat as nonterminal if known, else terminal keyword
            if t.v in self.nonterms:
                return ("nt", t.v)
            return ("lit", t.v)
        return ("lit", t.v)

def _parse_grammar(text: str):
    # First pass: collect LHS
    lines = text.splitlines()
    raw_rules: Dict[str, str] = {{}}
    order: List[str] = []
    cur_lhs = None
    cur_rhs = []
    def _flush():
        nonlocal cur_lhs, cur_rhs
        if cur_lhs is not None:
            rhs = " ".join(cur_rhs).strip()
            if rhs:
                raw_rules[cur_lhs] = rhs
                order.append(cur_lhs)
        cur_lhs = None
        cur_rhs = []
    for line in lines:
        s = _strip_comments(line)
        if not s:
            continue
        # detect new rule line with ::= or ->
        if "::=" in s or "->" in s:
            _flush()
            m = re.split(r"::=|->", s, maxsplit=1)
            if len(m) != 2:
                continue
            lhs = m[0].strip()
            rhs = m[1].strip()
            if lhs.startswith("<") and lhs.endswith(">"):
                lhs = lhs[1:-1].strip()
            # strip trailing ';' if present, keep if it's inside literals (already stripped)
            if rhs.endswith(";"):
                rhs = rhs[:-1].strip()
            cur_lhs = lhs
            cur_rhs = [rhs] if rhs else []
        else:
            # continuation line
            if cur_lhs is None:
                continue
            if s.endswith(";"):
                s2 = s[:-1].strip()
                if s2:
                    cur_rhs.append(s2)
                _flush()
            else:
                cur_rhs.append(s)
    _flush()

    nonterms = set(raw_rules.keys())
    rules_ast: Dict[str, Any] = {{}}
    for lhs, rhs in raw_rules.items():
        toks = _tokenize_ebnf(rhs)
        p = _EBNFParser(toks, nonterms)
        ast = p.parse_expr()
        rules_ast[lhs] = ast
    return rules_ast, order

_RULES, _ORDER = _parse_grammar(GRAMMAR_TEXT) if GRAMMAR_TEXT else ({{}}, [])
_NONTERMS = set(_RULES.keys())

def _pick_start_symbol() -> Optional[str]:
    if not _ORDER:
        return None
    # prefer common names
    pref = ("sql", "statement", "stmt", "query", "program", "input")
    candidates = []
    for nt in _ORDER:
        l = nt.lower()
        score = 0
        for i, p in enumerate(pref):
            if p in l:
                score += (len(pref) - i) * 10
        if l in ("statement", "stmt", "query", "sql_stmt", "sql_stmt_list", "program", "start"):
            score += 100
        candidates.append((score, nt))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else _ORDER[0]

_START = _pick_start_symbol()

# ---------------- Generation helpers ----------------

_RNG = random.Random(0xC0FFEE)
_ALPHA = string.ascii_letters + "_"
_ALNUM = string.ascii_letters + string.digits + "_$"

_PLACEHOLDER_TERMS = {{
    "IDENT", "IDENTIFIER", "ID", "NAME", "TABLE", "TABLE_NAME", "COLUMN", "COLUMN_NAME",
    "STRING", "STRING_LITERAL", "STR", "TEXT",
    "NUMBER", "NUM", "INT", "INTEGER", "FLOAT", "REAL", "DECIMAL",
    "BOOL", "BOOLEAN",
    "PARAM", "PARAMETER",
}}

def _rand_ident(r: random.Random) -> str:
    # Mix of plain and quoted identifiers
    base = r.choice(["t", "tbl", "user", "orders", "x", "col", "c", "idx", "v", "tmp", "schema"])
    suffix = str(r.randrange(0, 1000))
    s = base + suffix
    mode = r.randrange(0, 6)
    if mode == 0:
        return s
    if mode == 1:
        return "_" + s
    if mode == 2:
        return '"' + s.replace('"', '""') + '"'
    if mode == 3:
        return "`" + s.replace("`", "``") + "`"
    if mode == 4:
        return "[" + s.replace("]", "]]") + "]"
    # odd unicode
    return s + r.choice(["Å", "ß", "Δ", "Ж", "中"])

def _rand_string(r: random.Random) -> str:
    # include escapes/doubled quotes
    parts = [
        "a", "b", "test", "x", "0", "1", "NULL", "O'Reilly", "line\\n", "tab\\t",
        "/*c*/", "--c", "☃", "中", "€", "''", "\\\\", "a''b", "x%y", "_wild_"
    ]
    s = r.choice(parts)
    # sometimes make long
    if r.random() < 0.1:
        s = s * r.randrange(5, 40)
    # SQL standard escaping by doubling single quote
    s = s.replace("'", "''")
    return "'" + s + "'"

def _rand_number(r: random.Random) -> str:
    t = r.randrange(0, 8)
    if t == 0:
        return str(r.randrange(-10, 11))
    if t == 1:
        return str(r.randrange(0, 1000000))
    if t == 2:
        return str(r.randrange(-1000000, 1000000))
    if t == 3:
        return f"0x{{r.randrange(0, 1<<32):x}}"
    if t == 4:
        return f"{{r.randrange(0, 1000)}}.{{r.randrange(0, 1000)}}"
    if t == 5:
        return f"{{r.randrange(0, 1000)}}.{{r.randrange(0, 1000)}}e{{r.randrange(-20, 21)}}"
    if t == 6:
        return "1e309"  # inf-ish
    return "0.0"

def _maybe_case_kw(tok: str, r: random.Random) -> str:
    if not tok:
        return tok
    if tok[0] in ("'", '"', "`", "["):
        return tok
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok) is None:
        return tok
    # Try to case-mangle known keywords; otherwise sometimes.
    upper = tok.upper()
    if upper in _KW_SET or (upper in EXTRA_KEYWORDS):
        mode = r.randrange(0, 5)
        if mode == 0:
            return upper
        if mode == 1:
            return upper.lower()
        if mode == 2:
            return upper.capitalize()
        if mode == 3:
            return "".join((c.lower() if r.random() < 0.5 else c.upper()) for c in upper)
        return tok
    if r.random() < 0.05:
        return "".join((c.lower() if r.random() < 0.5 else c.upper()) for c in tok)
    return tok

def _lit_value(lit: str, r: random.Random) -> List[str]:
    # lit from grammar may come as 'SELECT' or "SELECT" or raw token like ,
    if not lit:
        return []
    if lit in ("ε", "EPS", "EPSILON"):
        return []
    if (lit[0] == "'" and lit[-1] == "'") or (lit[0] == '"' and lit[-1] == '"'):
        # Unquote grammar literals, but preserve punctuation and multiword
        inner = lit[1:-1]
        inner = inner.replace("\\\\", "\\\\")
        inner = inner.replace("''", "'") if lit[0] == "'" else inner
        inner = inner.replace('""', '"') if lit[0] == '"' else inner
        # If it's multiword like "PRIMARY KEY" split into tokens
        if " " in inner.strip():
            return [p for p in inner.strip().split() if p]
        return [inner]
    # Placeholder terminals?
    u = lit.upper()
    if u in _PLACEHOLDER_TERMS:
        if "STR" in u or "TEXT" in u:
            return [_rand_string(r)]
        if "NUM" in u or "INT" in u or "FLOAT" in u or "REAL" in u or "DEC" in u:
            return [_rand_number(r)]
        return [_rand_ident(r)]
    return [lit]

def _heuristic_for_nt(name: str, r: random.Random) -> List[str]:
    n = name.lower()
    if "string" in n or "text" in n or "char" in n or "varchar" in n or "literal" in n:
        return [_rand_string(r)]
    if "int" in n or "num" in n or "real" in n or "float" in n or "dec" in n:
        return [_rand_number(r)]
    if "ident" in n or "name" in n or "table" in n or "column" in n or "schema" in n:
        return [_rand_ident(r)]
    if "bool" in n:
        return [r.choice(["TRUE", "FALSE", "0", "1"])]
    if "null" in n:
        return ["NULL"]
    if "op" in n or "operator" in n:
        return [r.choice(["=", "!=", "<>", "<", ">", "<=", ">=", "+", "-", "*", "/", "%", "||", "AND", "OR"])]
    if "ws" in n or "space" in n:
        return []
    return [_rand_ident(r)]

def _flatten_seq(node) -> List[Any]:
    # normalize sequences/alts
    tag = node[0]
    if tag == "seq":
        parts = []
        for c in node[1]:
            if isinstance(c, tuple) and c and c[0] == "seq":
                parts.extend(_flatten_seq(c))
            else:
                parts.append(c)
        return parts
    return [node]

def _node_minlen(node, memo_node, memo_nt, stack_nt) -> int:
    if not isinstance(node, tuple) or not node:
        return 0
    key = id(node)
    if key in memo_node:
        return memo_node[key]
    tag = node[0]
    if tag == "lit":
        v = node[1]
        if v in ("ε", "EPS", "EPSILON"):
            memo_node[key] = 0
            return 0
        # multiword literal gets split
        if (v and (v[0] in ("'", '"')) and " " in v[1:-1].strip()):
            memo_node[key] = max(1, len(v[1:-1].strip().split()))
            return memo_node[key]
        memo_node[key] = 1
        return 1
    if tag == "nt":
        nt = node[1]
        if nt in memo_nt:
            memo_node[key] = memo_nt[nt]
            return memo_node[key]
        if nt in stack_nt:
            memo_node[key] = 10**6
            return memo_node[key]
        stack_nt.add(nt)
        ast = _RULES.get(nt)
        if ast is None:
            val = 1
        else:
            val = _node_minlen(ast, memo_node, memo_nt, stack_nt)
        stack_nt.remove(nt)
        memo_nt[nt] = val
        memo_node[key] = val
        return val
    if tag == "seq":
        s = 0
        for c in node[1]:
            s += _node_minlen(c, memo_node, memo_nt, stack_nt)
            if s > 10**6:
                s = 10**6
                break
        memo_node[key] = s
        return s
    if tag == "alt":
        m = 10**6
        for c in node[1]:
            l = _node_minlen(c, memo_node, memo_nt, stack_nt)
            if l < m:
                m = l
        memo_node[key] = m
        return m
    if tag == "opt":
        memo_node[key] = 0
        return 0
    if tag == "rep":
        child, minr, _maxr = node[1], node[2], node[3]
        cl = _node_minlen(child, memo_node, memo_nt, stack_nt)
        v = minr * cl
        memo_node[key] = v
        return v
    memo_node[key] = 1
    return 1

_MEMO_NODE = {{}}
_MEMO_NT = {{}}
for _nt, _ast in _RULES.items():
    _node_minlen(("nt", _nt), _MEMO_NODE, _MEMO_NT, set())

def _expand(node, r: random.Random, depth: int, max_depth: int, stack: set) -> List[str]:
    if not isinstance(node, tuple) or not node:
        return []
    tag = node[0]
    if tag == "lit":
        return _lit_value(node[1], r)
    if tag == "nt":
        nt = node[1]
        if depth >= max_depth or nt in stack:
            return _heuristic_for_nt(nt, r)
        ast = _RULES.get(nt)
        if ast is None:
            return _heuristic_for_nt(nt, r)
        stack.add(nt)
        out = _expand(ast, r, depth + 1, max_depth, stack)
        stack.remove(nt)
        return out
    if tag == "seq":
        out: List[str] = []
        for c in node[1]:
            out.extend(_expand(c, r, depth, max_depth, stack))
        return out
    if tag == "alt":
        opts = node[1]
        if not opts:
            return []
        # bias to shorter expansions when deep
        if depth > max_depth * 0.6:
            # select among few shortest
            scored = []
            for c in opts:
                ml = _node_minlen(c, _MEMO_NODE, _MEMO_NT, set())
                scored.append((ml, c))
            scored.sort(key=lambda x: x[0])
            k = min(len(scored), 4)
            choice = scored[r.randrange(0, k)][1]
            return _expand(choice, r, depth, max_depth, stack)
        # otherwise random weighted by inverse minlen
        weights = []
        total = 0.0
        for c in opts:
            ml = _node_minlen(c, _MEMO_NODE, _MEMO_NT, set())
            w = 1.0 / (1.0 + ml)
            weights.append(w)
            total += w
        x = r.random() * total
        acc = 0.0
        for w, c in zip(weights, opts):
            acc += w
            if acc >= x:
                return _expand(c, r, depth, max_depth, stack)
        return _expand(opts[-1], r, depth, max_depth, stack)
    if tag == "opt":
        if r.random() < 0.55:
            return _expand(node[1], r, depth, max_depth, stack)
        return []
    if tag == "rep":
        child, minr, maxr = node[1], node[2], node[3]
        if depth > max_depth * 0.7:
            rep = minr
        else:
            cap = maxr if maxr >= 0 else 3
            rep = r.randrange(minr, cap + 1)
        out: List[str] = []
        for _ in range(rep):
            out.extend(_expand(child, r, depth, max_depth, stack))
        return out
    return []

_PUNCT_NO_SPACE_BEFORE = {{",", ";", ")", "]", "}}", ".", ":"}}
_PUNCT_NO_SPACE_AFTER = {{"(", "[", "{{", ".", ":"}}
_BINOPS = {{"=", "!=", "<>", "<", ">", "<=", ">=", "+", "-", "*", "/", "%", "||", "AND", "OR", "LIKE", "IN", "IS"}}

def _build_sql(tokens: List[str], r: random.Random) -> str:
    # Apply keyword casing and assemble with whitespace/comment perturbations.
    toks = [t for t in tokens if t is not None and t != ""]
    # normalize multi-token sequences that might have gotten glued
    out_parts: List[str] = []
    prev = None
    for tok in toks:
        tok = _maybe_case_kw(tok, r)
        if prev is None:
            out_parts.append(tok)
            prev = tok
            continue
        # decide separator
        sep = " "
        if tok in _PUNCT_NO_SPACE_BEFORE:
            sep = ""
        if prev in _PUNCT_NO_SPACE_AFTER:
            sep = ""
        # optionally add whitespace/comments when sep is space
        if sep == " ":
            roll = r.random()
            if roll < 0.06:
                sep = "\\n"
            elif roll < 0.10:
                sep = "\\t"
            elif roll < 0.14:
                sep = "  "
            elif roll < 0.18:
                sep = "/*c*/"
            elif roll < 0.22:
                sep = " --c\\n "
            else:
                sep = " "
            # sometimes omit spaces around dots/operators
            if tok == "." or prev == ".":
                sep = ""
        # sometimes omit space before '(' to resemble function calls
        if tok == "(" and sep == " " and prev and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", prev or ""):
            if r.random() < 0.55:
                sep = ""
        out_parts.append(sep + tok)
        prev = tok
    s = "".join(out_parts).strip()
    # Sometimes add trailing semicolon or weird trailing comment/space
    if s and r.random() < 0.7 and not s.endswith(";"):
        if r.random() < 0.85:
            s += ";"
        else:
            s += " ;"
    if r.random() < 0.08:
        s = " " * r.randrange(0, 3) + s + " " * r.randrange(0, 3)
    if r.random() < 0.04:
        s = "/*lead*/" + s
    if r.random() < 0.04:
        s = s + "/*trail*/"
    return s

def _mutate_sql(s: str, r: random.Random) -> str:
    if not s:
        return s
    mode = r.randrange(0, 10)
    if mode == 0:
        # drop a random chunk
        if len(s) < 6:
            return s
        a = r.randrange(0, len(s) - 1)
        b = r.randrange(a + 1, min(len(s), a + 1 + r.randrange(1, 25)))
        return s[:a] + s[b:]
    if mode == 1:
        # duplicate a random chunk
        if len(s) < 6:
            return s + s
        a = r.randrange(0, len(s) - 1)
        b = r.randrange(a + 1, min(len(s), a + 1 + r.randrange(1, 25)))
        chunk = s[a:b]
        return s[:b] + chunk + s[b:]
    if mode == 2:
        # random case flip
        return "".join((c.lower() if (c.isalpha() and r.random() < 0.5) else (c.upper() if c.isalpha() else c)) for c in s)
    if mode == 3:
        # inject comment
        pos = r.randrange(0, len(s))
        return s[:pos] + r.choice(["/*x*/", " --x\\n ", "\\n", "\\t"]) + s[pos:]
    if mode == 4:
        # replace some quotes
        return s.replace("'", "''") if r.random() < 0.7 else s.replace('"', '""')
    if mode == 5:
        # remove semicolons
        return s.replace(";", "")
    if mode == 6:
        # add unmatched paren/bracket to trigger error paths
        return s + r.choice([")", "(", "]", "["])
    if mode == 7:
        # swap operators
        return re.sub(r"\\bAND\\b", "OR", s, flags=re.I) if r.random() < 0.5 else re.sub(r"\\bOR\\b", "AND", s, flags=re.I)
    if mode == 8:
        # sprinkle commas
        pos = r.randrange(0, len(s))
        return s[:pos] + "," + s[pos:]
    # random truncation
    cut = r.randrange(1, max(2, len(s)))
    return s[:cut]

# keyword set for casing
_KW_SET = set([k.upper() for k in EXTRA_KEYWORDS] + [
    "SELECT","FROM","WHERE","GROUP","BY","HAVING","ORDER","LIMIT","OFFSET",
    "INSERT","INTO","VALUES","UPDATE","SET","DELETE",
    "CREATE","TABLE","DROP","ALTER","INDEX","VIEW","TRIGGER",
    "DISTINCT","ALL","AS","AND","OR","NOT","NULL","IS","IN","LIKE",
    "BETWEEN","EXISTS","CASE","WHEN","THEN","ELSE","END",
    "INNER","LEFT","RIGHT","FULL","OUTER","CROSS","JOIN","ON","USING",
    "UNION","INTERSECT","EXCEPT","WITH","RECURSIVE",
    "PRIMARY","KEY","FOREIGN","REFERENCES","CHECK","UNIQUE","DEFAULT",
    "BEGIN","COMMIT","ROLLBACK","TRANSACTION",
])

# ---------------- Template seeds (broad coverage) ----------------

def _templates(r: random.Random) -> List[str]:
    t = []
    # DDL
    tn = _rand_ident(r)
    cn1 = _rand_ident(r)
    cn2 = _rand_ident(r)
    t.append(f"CREATE TABLE {{tn}} ({{cn1}} INT, {{cn2}} TEXT);")
    t.append(f"CREATE TABLE {{tn}} (id INTEGER PRIMARY KEY, name TEXT, price REAL, created_at TEXT);")
    t.append(f"CREATE TABLE {{tn}} (id INT PRIMARY KEY, x INT, y INT, z TEXT, CHECK (x >= 0));")
    t.append(f"DROP TABLE {{tn}};")
    t.append(f"CREATE INDEX idx_{{tn}}_{{cn1}} ON {{tn}} ({{cn1}});")
    t.append(f"DROP INDEX idx_{{tn}}_{{cn1}};")
    # DML
    t.append(f"INSERT INTO {{tn}} ({{cn1}}, {{cn2}}) VALUES ({{_rand_number(r)}}, {{_rand_string(r)}});")
    t.append(f"INSERT INTO {{tn}} VALUES ({{_rand_number(r)}}, {{_rand_string(r)}});")
    t.append(f"UPDATE {{tn}} SET {{cn1}} = {{_rand_number(r)}}, {{cn2}} = {{_rand_string(r)}} WHERE {{cn1}} >= 0;")
    t.append(f"DELETE FROM {{tn}} WHERE {{cn1}} < 10;")
    # SELECT variations
    t.append(f"SELECT * FROM {{tn}};")
    t.append(f"SELECT {{cn1}}, {{cn2}} FROM {{tn}} WHERE {{cn1}} BETWEEN 1 AND 10;")
    t.append(f"SELECT DISTINCT {{cn1}} FROM {{tn}} ORDER BY {{cn1}} DESC LIMIT 10 OFFSET 1;")
    t.append(f"SELECT {{cn1}} + 1 AS k FROM {{tn}} WHERE {{cn2}} LIKE '%x%';")
    t.append(f"SELECT CASE WHEN {{cn1}} IS NULL THEN 0 ELSE {{cn1}} END FROM {{tn}};")
    t.append(f"SELECT {{cn1}} FROM {{tn}} WHERE {{cn1}} IN (1,2,3,4,5);")
    t.append(f"SELECT a.{{cn1}} FROM {{tn}} a JOIN {{tn}} b ON a.{{cn1}} = b.{{cn1}};")
    t.append(f"SELECT {{cn1}} FROM {{tn}} WHERE EXISTS (SELECT 1 FROM {{tn}});")
    t.append(f"WITH cte AS (SELECT {{cn1}} FROM {{tn}}) SELECT * FROM cte;")
    # Transaction-ish
    t.append("BEGIN;")
    t.append("COMMIT;")
    t.append("ROLLBACK;")
    # Edge tokens / tokenizer paths
    t.append("SELECT 'a''b', \"q\"\"w\", `x``y`, [z]]w];")
    t.append("SELECT 0x1, 1e-9, 1.2e+3, -0, 1e309;")
    t.append("SELECT /*c*/1 --x\\n FROM t0;")
    # Likely error paths
    t.append("SELECT FROM;")
    t.append("INSERT INTO VALUES ();")
    t.append("CREATE TABLE (id INT);")
    return t

# Build an initial corpus: grammar expansions + templates.
_CORPUS: List[str] = []
if _START and _RULES:
    rr = random.Random(0xABCDEF)
    for _ in range(250):
        toks = _expand(("nt", _START), rr, 0, 12, set())
        s = _build_sql(toks, rr)
        if s:
            _CORPUS.append(s)
# Add templates
rr2 = random.Random(0x12345)
_CORPUS.extend(_templates(rr2))
# Add some raw oddities
_CORPUS.extend([
    "", " ", ";", ";;", "/*", "*/", "--\\n", "/*x*/", "SELECT", "SELECT;", "SELECT 1", "SELECT 1;",
    "SELECT '", "SELECT \"", "SELECT `", "SELECT [", "SELECT 1 FROM", "SELECT (1", "SELECT 1))",
])

# Deduplicate but keep order
_seen = set()
_tmp = []
for s in _CORPUS:
    if s not in _seen:
        _seen.add(s)
        _tmp.append(s)
_CORPUS = _tmp

# ---------------- Main fuzz entrypoint ----------------

_START_TIME = None
_CALLS = 0

def fuzz(parse_sql):
    global _START_TIME, _CALLS, _CORPUS
    if _START_TIME is None:
        _START_TIME = time.perf_counter()
    _CALLS += 1
    elapsed = time.perf_counter() - _START_TIME

    # Budgeting: adapt batch size based on elapsed time and try to keep parse_sql calls moderate.
    if elapsed < 8.0:
        batch = 900
        max_depth = 14
    elif elapsed < 20.0:
        batch = 700
        max_depth = 13
    elif elapsed < 35.0:
        batch = 520
        max_depth = 12
    elif elapsed < 50.0:
        batch = 350
        max_depth = 11
    else:
        batch = 200
        max_depth = 10

    r = _RNG
    stmts: List[str] = []
    corpus_len = len(_CORPUS)

    # Ensure some templates each round to hit specific constructs
    tmpl = _templates(random.Random(r.randrange(1 << 30)))
    stmts.extend(tmpl[:min(20, len(tmpl))])

    # Generate grammar-based statements if possible
    do_grammar = bool(_START and _RULES)

    for i in range(batch - len(stmts)):
        p = r.random()
        if p < 0.60 and do_grammar:
            toks = _expand(("nt", _START), r, 0, max_depth, set())
            s = _build_sql(toks, r)
        elif p < 0.82:
            # take from corpus
            if corpus_len:
                s = _CORPUS[r.randrange(0, corpus_len)]
            else:
                s = r.choice(tmpl)
        else:
            # synthetic invalid-ish strings
            a = _maybe_case_kw(r.choice(EXTRA_KEYWORDS) if EXTRA_KEYWORDS else "SELECT", r)
            b = _maybe_case_kw(r.choice(EXTRA_KEYWORDS) if EXTRA_KEYWORDS else "FROM", r)
            s = f"{{a}} {{_rand_ident(r)}} {{b}} {{_rand_ident(r)}} WHERE {{_rand_ident(r)}} = {{_rand_string(r)}};"
            if r.random() < 0.3:
                s = s.replace("WHERE", "")
            if r.random() < 0.2:
                s += r.choice([")", "(", "/*", "--"])

        # Mutate some
        if r.random() < 0.22:
            s = _mutate_sql(s, r)
        if s is None:
            continue
        s = s.strip()
        if s == "" and r.random() < 0.9:
            # keep some empties but not too many
            continue
        stmts.append(s)

    # Shuffle slightly to vary parsing order
    if len(stmts) > 64:
        r.shuffle(stmts)

    # Parse as a single batch (one parse_sql call per fuzz() invocation)
    parse_sql(stmts)

    # Update corpus: sample some generated statements (keep bounded)
    for s in stmts[: min(60, len(stmts))]:
        if s and len(s) <= 800 and r.random() < 0.35:
            _CORPUS.append(s)
    if len(_CORPUS) > 6000:
        # keep some diversity, drop random slice
        keep = 4200
        # preserve a prefix of templates-ish and random sample of rest
        fixed = _CORPUS[:300]
        rest = _CORPUS[300:]
        r.shuffle(rest)
        _CORPUS = fixed + rest[: max(0, keep - len(fixed))]

    # Stop near end of time or after enough calls
    if elapsed > 58.0:
        return False
    if _CALLS >= 60 and elapsed > 20.0:
        return False
    return True
"""
        return {"code": code}