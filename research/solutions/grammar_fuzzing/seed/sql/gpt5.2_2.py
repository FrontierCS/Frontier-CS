import os
import sys
import re
import random
import importlib
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set, Union, Iterable


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _strip_line_comment(s: str) -> str:
    s = re.sub(r"//.*$", "", s)
    s = re.sub(r"#.*$", "", s)
    return s


def _split_rules(raw: str) -> List[str]:
    lines = raw.splitlines()
    merged = []
    cur = ""
    for line in lines:
        line = _strip_line_comment(line).rstrip()
        if not line.strip():
            continue
        if "::=" in line or "->" in line:
            if cur:
                merged.append(cur.strip())
            cur = line.strip()
        else:
            if cur and (line.lstrip().startswith("|") or line.lstrip().startswith(") |") or line.lstrip().startswith("] |") or line.lstrip().startswith("} |")):
                cur += " " + line.strip()
            elif cur:
                cur += " " + line.strip()
            else:
                cur = line.strip()
    if cur:
        merged.append(cur.strip())
    return merged


_TOKEN_RE = re.compile(
    r"""
    (?:'[^']*(?:''[^']*)*') |                 # single-quoted with doubled quotes
    (?:"[^"]*(?:""[^"]*)*") |                 # double-quoted with doubled quotes
    (?:<[^>]+>) |                             # angle-bracket nonterminal
    (?:\:\:\=|->) |                           # assignment
    (?:<=|>=|<>|!=) |                         # 2-char ops
    (?:[()\[\]{}|*+?;,./=<>-]) |              # single char symbols
    (?:[A-Za-z_][A-Za-z0-9_]*) |              # identifiers
    (?:\d+(?:\.\d+)?)                         # number
    """,
    re.VERBOSE,
)


def _tokenize_rhs(rhs: str) -> List[str]:
    toks = _TOKEN_RE.findall(rhs)
    out = []
    for t in toks:
        t = t.strip()
        if t:
            out.append(t)
    return out


@dataclass(frozen=True)
class _Sym:
    name: str
    is_nonterm: bool


@dataclass(frozen=True)
class _Seq:
    items: Tuple[" _Node", ...]  # type: ignore


@dataclass(frozen=True)
class _Alt:
    options: Tuple[" _Node", ...]  # type: ignore


@dataclass(frozen=True)
class _Opt:
    node: " _Node"  # type: ignore


@dataclass(frozen=True)
class _Rep:
    node: " _Node"  # type: ignore
    min_rep: int
    max_rep: int


_Node = Union[_Sym, _Seq, _Alt, _Opt, _Rep]


class _EBNFParser:
    def __init__(self, tokens: List[str], nonterminals: Set[str]):
        self.toks = tokens
        self.i = 0
        self.nonterminals = nonterminals

    def _peek(self) -> Optional[str]:
        if self.i >= len(self.toks):
            return None
        return self.toks[self.i]

    def _eat(self, t: str) -> bool:
        if self._peek() == t:
            self.i += 1
            return True
        return False

    def parse(self) -> _Node:
        node = self._parse_alt()
        return node

    def _parse_alt(self) -> _Node:
        seqs = [self._parse_seq()]
        while self._eat("|"):
            seqs.append(self._parse_seq())
        if len(seqs) == 1:
            return seqs[0]
        return _Alt(tuple(seqs))

    def _parse_seq(self) -> _Node:
        items: List[_Node] = []
        while True:
            p = self._peek()
            if p is None or p in (")", "]", "}", "|"):
                break
            items.append(self._parse_term())
        if not items:
            return _Seq(tuple())
        if len(items) == 1:
            return items[0]
        return _Seq(tuple(items))

    def _parse_term(self) -> _Node:
        base = self._parse_factor()
        p = self._peek()
        if p in ("?", "*", "+"):
            self.i += 1
            if p == "?":
                return _Opt(base)
            if p == "*":
                return _Rep(base, 0, 2)
            if p == "+":
                return _Rep(base, 1, 2)
        return base

    def _parse_factor(self) -> _Node:
        p = self._peek()
        if p is None:
            return _Seq(tuple())
        if self._eat("("):
            inner = self._parse_alt()
            self._eat(")")
            return inner
        if self._eat("["):
            inner = self._parse_alt()
            self._eat("]")
            return _Opt(inner)
        if self._eat("{"):
            inner = self._parse_alt()
            self._eat("}")
            return _Rep(inner, 0, 2)
        self.i += 1
        tok = p

        if tok.startswith("<") and tok.endswith(">"):
            name = tok[1:-1].strip()
            return _Sym(name, True)

        if tok.startswith("'") and tok.endswith("'"):
            return _Sym(tok[1:-1].replace("''", "'"), False)
        if tok.startswith('"') and tok.endswith('"'):
            return _Sym(tok[1:-1].replace('""', '"'), False)

        is_nonterm = tok in self.nonterminals and tok.lower() not in ("select", "from", "where")
        return _Sym(tok, is_nonterm)


class _Grammar:
    def __init__(self, rules: Dict[str, _Node], start: str):
        self.rules = rules
        self.start = start
        self.term_freq: Dict[str, int] = {}
        self._compute_term_freq()

    def _compute_term_freq(self) -> None:
        freq: Dict[str, int] = {}
        def walk(n: _Node):
            if isinstance(n, _Sym):
                if not n.is_nonterm:
                    t = n.name
                    if t:
                        freq[t.upper()] = freq.get(t.upper(), 0) + 1
            elif isinstance(n, _Seq):
                for c in n.items:
                    walk(c)
            elif isinstance(n, _Alt):
                for c in n.options:
                    walk(c)
            elif isinstance(n, _Opt):
                walk(n.node)
            elif isinstance(n, _Rep):
                walk(n.node)
        for n in self.rules.values():
            walk(n)
        self.term_freq = freq

    def _placeholder(self, name: str, rng: random.Random) -> str:
        u = name.upper()
        if u in ("IDENT", "IDENTIFIER", "ID", "NAME", "COLUMN", "COLUMN_NAME", "TABLE", "TABLE_NAME"):
            return rng.choice(["t", "t1", "t2", "col", "id", "name"])
        if u in ("STRING", "STR", "TEXT", "CHAR", "VARCHAR"):
            return rng.choice(["'x'", "'O''Reilly'", "''", "'%_%'"])
        if u in ("NUMBER", "NUM", "INT", "INTEGER", "SMALLINT", "BIGINT"):
            return rng.choice(["0", "1", "2", "10", "42"])
        if u in ("FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC"):
            return rng.choice(["1.5", "0.0", "3.1415"])
        if u in ("BOOL", "BOOLEAN"):
            return rng.choice(["TRUE", "FALSE"])
        if u in ("NULL",):
            return "NULL"
        if u in ("STAR",):
            return "*"
        if u in ("COMMA",):
            return ","
        return "x"

    def _expand(self, node: _Node, rng: random.Random, depth: int, max_depth: int) -> List[str]:
        if depth > max_depth:
            if isinstance(node, _Sym) and node.is_nonterm:
                return []
            if isinstance(node, _Sym):
                return [node.name]
            return []
        if isinstance(node, _Sym):
            if node.is_nonterm:
                name = node.name
                if name not in self.rules:
                    return [self._placeholder(name, rng)]
                return self._expand_rule(name, rng, depth + 1, max_depth)
            else:
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", node.name) and node.name.upper() in ("IDENTIFIER", "IDENT", "NAME", "NUMBER", "INT", "INTEGER", "STRING", "FLOAT", "BOOLEAN", "BOOL"):
                    return [self._placeholder(node.name, rng)]
                return [node.name]
        if isinstance(node, _Seq):
            out: List[str] = []
            for it in node.items:
                out.extend(self._expand(it, rng, depth + 1, max_depth))
            return out
        if isinstance(node, _Alt):
            scored: List[Tuple[int, _Node]] = []
            for opt in node.options:
                terms = self._collect_terminals(opt, limit=50)
                s = sum(self.term_freq.get(t.upper(), 1) for t in terms)
                scored.append((s, opt))
            scored.sort(key=lambda x: x[0])
            pool = [n for _, n in scored[: min(3, len(scored))]]
            chosen = rng.choice(pool) if pool else rng.choice(list(node.options))
            return self._expand(chosen, rng, depth + 1, max_depth)
        if isinstance(node, _Opt):
            if rng.random() < 0.55:
                return self._expand(node.node, rng, depth + 1, max_depth)
            return []
        if isinstance(node, _Rep):
            if node.max_rep <= node.min_rep:
                k = node.min_rep
            else:
                k = rng.randint(node.min_rep, node.max_rep)
            out: List[str] = []
            for _ in range(k):
                out.extend(self._expand(node.node, rng, depth + 1, max_depth))
            return out
        return []

    def _collect_terminals(self, node: _Node, limit: int = 200) -> List[str]:
        out: List[str] = []
        def walk(n: _Node):
            nonlocal out
            if len(out) >= limit:
                return
            if isinstance(n, _Sym):
                if not n.is_nonterm:
                    out.append(n.name)
            elif isinstance(n, _Seq):
                for c in n.items:
                    walk(c)
            elif isinstance(n, _Alt):
                for c in n.options:
                    walk(c)
            elif isinstance(n, _Opt):
                walk(n.node)
            elif isinstance(n, _Rep):
                walk(n.node)
        walk(node)
        return out

    def _expand_rule(self, name: str, rng: random.Random, depth: int, max_depth: int) -> List[str]:
        node = self.rules[name]
        return self._expand(node, rng, depth, max_depth)

    def generate(self, rng: random.Random, max_depth: int = 10) -> str:
        toks = self._expand_rule(self.start, rng, 0, max_depth)
        s = " ".join(toks)
        s = re.sub(r"\s+([,;)\]])", r"\1", s)
        s = re.sub(r"([( \[])\s+", r"\1", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s


def _load_grammar(grammar_path: str) -> Optional[_Grammar]:
    try:
        raw = _read_text(grammar_path)
    except Exception:
        return None
    rules_lines = _split_rules(raw)
    lhs_list: List[str] = []
    for line in rules_lines:
        if "::=" in line:
            lhs = line.split("::=", 1)[0].strip()
        elif "->" in line:
            lhs = line.split("->", 1)[0].strip()
        else:
            continue
        if lhs.startswith("<") and lhs.endswith(">"):
            lhs = lhs[1:-1].strip()
        lhs_list.append(lhs)
    nonterminals = set(lhs_list)
    rules: Dict[str, _Node] = {}
    for line in rules_lines:
        if "::=" in line:
            lhs, rhs = line.split("::=", 1)
        elif "->" in line:
            lhs, rhs = line.split("->", 1)
        else:
            continue
        lhs = lhs.strip()
        rhs = rhs.strip()
        if lhs.startswith("<") and lhs.endswith(">"):
            lhs = lhs[1:-1].strip()
        toks = _tokenize_rhs(rhs)
        if not toks:
            continue
        parser = _EBNFParser(toks, nonterminals)
        try:
            node = parser.parse()
        except Exception:
            continue
        rules[lhs] = node
    if not rules:
        return None
    start_candidates = [
        "sql",
        "statement_list",
        "statements",
        "program",
        "script",
        "statement",
        "stmt",
        "sql_stmt",
        "sql_statement",
        "query",
        "select_statement",
        "select_stmt",
    ]
    start = None
    for c in start_candidates:
        if c in rules:
            start = c
            break
    if start is None:
        start = next(iter(rules.keys()))
    return _Grammar(rules, start)


def _extract_keywords_from_tokenizer(tokenizer_path: str) -> Set[str]:
    try:
        txt = _read_text(tokenizer_path)
    except Exception:
        return set()
    kws = set(re.findall(r"['\"]([A-Z][A-Z0-9_]+)['\"]", txt))
    kws |= set(re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", txt))
    common = {
        "SELECT", "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "OFFSET",
        "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE",
        "CREATE", "TABLE", "DROP", "ALTER", "ADD", "COLUMN", "VIEW", "INDEX",
        "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "ON", "USING",
        "DISTINCT", "UNION", "ALL", "INTERSECT", "EXCEPT",
        "WITH", "AS", "CASE", "WHEN", "THEN", "ELSE", "END",
        "NULL", "IS", "NOT", "AND", "OR", "IN", "EXISTS", "BETWEEN", "LIKE", "ESCAPE",
        "TRUE", "FALSE", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CHECK", "DEFAULT", "UNIQUE",
        "CAST",
    }
    kws |= common
    return {k for k in kws if k.isupper()}


def _extract_words(stmt: str) -> Set[str]:
    return set(w.upper() for w in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", stmt))


def _unique_preserve(seq: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _try_import_parse_sql(resources_path: str):
    if resources_path not in sys.path:
        sys.path.insert(0, resources_path)
    try:
        pkg = importlib.import_module("sql_engine")
    except Exception:
        sql_engine_path = os.path.join(resources_path, "sql_engine")
        if os.path.isdir(sql_engine_path) and sql_engine_path not in sys.path:
            sys.path.insert(0, sql_engine_path)
        pkg = importlib.import_module("sql_engine")
    parse_sql = getattr(pkg, "parse_sql", None)
    if parse_sql is not None:
        return parse_sql
    try:
        parser_mod = importlib.import_module("sql_engine.parser")
        parse_sql = getattr(parser_mod, "parse_sql", None)
        if parse_sql is not None:
            return parse_sql
    except Exception:
        pass
    raise ImportError("Could not import parse_sql from sql_engine")


def _validate_stmt(parse_sql, stmt: str) -> bool:
    try:
        parse_sql(stmt)
        return True
    except Exception:
        return False


def _normalize_variants(stmt: str) -> List[str]:
    s = stmt.strip()
    variants = [s]
    if s.endswith(";"):
        variants.append(s[:-1].rstrip())
    else:
        variants.append(s + ";")
    variants = _unique_preserve([v for v in variants if v.strip()])
    return variants


class Solution:
    def solve(self, resources_path: str) -> list[str]:
        tokenizer_path = os.path.join(resources_path, "sql_engine", "tokenizer.py")
        grammar_path = os.path.join(resources_path, "sql_grammar.txt")

        parse_sql = _try_import_parse_sql(resources_path)
        known_kws = _extract_keywords_from_tokenizer(tokenizer_path)

        base_candidates = [
            "SELECT 1",
            "SELECT 1+2*3",
            "SELECT -1 AS n",
            "SELECT 'a' AS s",
            "SELECT 'O''Reilly' AS s",
            "SELECT NULL",
            "SELECT TRUE",
            "SELECT FALSE",
            "SELECT col FROM t",
            "SELECT t.col, t2.col2 FROM t JOIN t2 ON t.id = t2.id",
            "SELECT * FROM t WHERE a = 1",
            "SELECT * FROM t WHERE a <> 1",
            "SELECT * FROM t WHERE a != 1",
            "SELECT * FROM t WHERE a <= 1",
            "SELECT * FROM t WHERE a >= 1",
            "SELECT * FROM t WHERE a BETWEEN 1 AND 10",
            "SELECT * FROM t WHERE a IN (1, 2, 3)",
            "SELECT * FROM t WHERE a IN (SELECT id FROM t2)",
            "SELECT * FROM t WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t.id)",
            r"SELECT * FROM t WHERE a LIKE '%x\_%' ESCAPE '\'",
            "SELECT DISTINCT a FROM t",
            "SELECT a, COUNT(*) FROM t GROUP BY a HAVING COUNT(*) > 1",
            "SELECT a FROM t ORDER BY a DESC",
            "SELECT a FROM t ORDER BY 1",
            "SELECT a FROM t LIMIT 10 OFFSET 5",
            "SELECT a FROM (SELECT 1 AS a) sub",
            "WITH cte AS (SELECT 1 AS a) SELECT a FROM cte",
            "SELECT CASE WHEN a > 1 THEN 'big' ELSE 'small' END FROM t",
            "SELECT COALESCE(NULL, a, 0) FROM t",
            "SELECT CAST(1 AS INT)",
            "SELECT a IS NULL FROM t",
            "SELECT a IS NOT NULL FROM t",
            "SELECT a FROM t WHERE NOT (a = 1)",
            "SELECT a FROM t WHERE a = 1 OR b = 2 AND c = 3",
            "SELECT 1 UNION SELECT 2",
            "SELECT 1 UNION ALL SELECT 2",
            "SELECT 1 INTERSECT SELECT 1",
            "SELECT 1 EXCEPT SELECT 1",
            "INSERT INTO t (a, b) VALUES (1, 'x')",
            "INSERT INTO t VALUES (1, 'x'), (2, 'y')",
            "INSERT INTO t (a) SELECT 1",
            "UPDATE t SET a = 2 WHERE id = 1",
            "UPDATE t SET a = a + 1, b = 'z' WHERE id = 1",
            "DELETE FROM t WHERE id = 1",
            "CREATE TABLE t (id INT)",
            "CREATE TABLE t (id INT PRIMARY KEY, name TEXT NOT NULL, age INT DEFAULT 0)",
            "DROP TABLE t",
            "DROP TABLE IF EXISTS t",
            "ALTER TABLE t ADD COLUMN x INT",
            "CREATE INDEX idx ON t (id)",
            "CREATE VIEW v AS SELECT 1 AS a",
            "SELECT /*comment*/ 1",
            "SELECT 1 -- comment",
            "SELECT\n  1\nFROM\n  t",
        ]

        valid: List[str] = []
        for cand in base_candidates:
            accepted = None
            for v in _normalize_variants(cand):
                if _validate_stmt(parse_sql, v):
                    accepted = v
                    break
            if accepted:
                valid.append(accepted)
        valid = _unique_preserve(valid)

        target_max = 28
        target_min = 18

        if len(valid) < target_min:
            grammar = _load_grammar(grammar_path)
            if grammar is not None:
                seed = 0
                try:
                    raw = _read_text(grammar_path)
                    seed = (hash(raw) ^ 0x9E3779B97F4A7C15) & 0xFFFFFFFF
                except Exception:
                    seed = 1337
                rng = random.Random(seed)
                for _ in range(400):
                    if len(valid) >= target_max:
                        break
                    s = grammar.generate(rng, max_depth=10)
                    if not s or len(s) > 280:
                        continue
                    if s.count("(") != s.count(")"):
                        continue
                    accepted = None
                    for v in _normalize_variants(s):
                        if _validate_stmt(parse_sql, v):
                            accepted = v
                            break
                    if accepted and accepted not in valid:
                        valid.append(accepted)

        # Greedy prune by keyword diversity proxy
        scored: List[Tuple[str, Set[str]]] = []
        for s in valid:
            kws = _extract_words(s)
            if known_kws:
                kws = {k for k in kws if k in known_kws}
            scored.append((s, kws))

        selected: List[str] = []
        covered: Set[str] = set()

        def stmt_kind(s: str) -> str:
            m = re.match(r"\s*([A-Za-z_]+)", s)
            return m.group(1).upper() if m else ""

        must_kinds = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "WITH"]
        kind_to_best: Dict[str, str] = {}
        for s, kws in scored:
            k = stmt_kind(s)
            if k in must_kinds and k not in kind_to_best:
                kind_to_best[k] = s

        for k in must_kinds:
            s = kind_to_best.get(k)
            if s and s not in selected:
                selected.append(s)
                for ss, kws in scored:
                    if ss == s:
                        covered |= kws
                        break

        remaining = [(s, kws) for (s, kws) in scored if s not in selected]
        while len(selected) < target_max and remaining:
            best_idx = -1
            best_gain = -1
            best_len = 10**9
            for i, (s, kws) in enumerate(remaining):
                gain = len(kws - covered)
                sl = len(s)
                if gain > best_gain or (gain == best_gain and sl < best_len):
                    best_gain = gain
                    best_idx = i
                    best_len = sl
            if best_idx < 0:
                break
            s, kws = remaining.pop(best_idx)
            if best_gain <= 0 and len(selected) >= target_min:
                break
            selected.append(s)
            covered |= kws

        selected = _unique_preserve([s.strip() for s in selected if s.strip()])
        if not selected:
            if _validate_stmt(parse_sql, "SELECT 1"):
                return ["SELECT 1"]
            if _validate_stmt(parse_sql, "SELECT 1;"):
                return ["SELECT 1;"]
            return ["SELECT 1"]
        return selected[:target_max]