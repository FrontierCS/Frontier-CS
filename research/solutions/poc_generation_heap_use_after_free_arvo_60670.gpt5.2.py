import io
import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union


Atom = str
Sexp = Union[Atom, List["Sexp"]]


def _read_tar_members_text(src_path: str, exts: Tuple[str, ...], max_bytes: int = 2_000_000) -> Iterable[Tuple[str, str]]:
    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return
    with tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            lower = name.lower()
            if not lower.endswith(exts):
                continue
            if m.size <= 0 or m.size > max_bytes:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(max_bytes + 1)
            except Exception:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            yield name, text


def _extract_keywords_from_source(src_path: str) -> Set[str]:
    keys: Set[str] = set()
    define_re = re.compile(r'^\s*#\s*define\s+CIL_KEY_[A-Z0-9_]+\s+"([^"]+)"', re.MULTILINE)
    for _, txt in _read_tar_members_text(src_path, (".h", ".c", ".inc", ".l", ".y"), max_bytes=3_000_000):
        for v in define_re.findall(txt):
            if v:
                keys.add(v)
    return keys


def _tokenize_cil(text: str) -> List[str]:
    # Remove line comments starting with ';' or '#'
    # Keep it simple: strip from first ';' or '#' to EOL if preceded by whitespace or line start.
    lines = []
    for line in text.splitlines():
        cut = None
        for ch in (";", "#"):
            idx = line.find(ch)
            if idx != -1:
                if idx == 0 or line[idx - 1].isspace():
                    if cut is None or idx < cut:
                        cut = idx
        if cut is not None:
            line = line[:cut]
        lines.append(line)
    s = "\n".join(lines)

    toks: List[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c == "(" or c == ")":
            toks.append(c)
            i += 1
            continue
        if c == '"':
            j = i + 1
            esc = False
            out = ['"']
            while j < n:
                ch = s[j]
                out.append(ch)
                if esc:
                    esc = False
                else:
                    if ch == "\\":
                        esc = True
                    elif ch == '"':
                        break
                j += 1
            toks.append("".join(out))
            i = j + 1
            continue
        j = i
        while j < n and (not s[j].isspace()) and s[j] not in "()":
            j += 1
        toks.append(s[i:j])
        i = j
    return toks


def _parse_sexps(tokens: List[str], max_nodes: int = 20000) -> List[Sexp]:
    idx = 0
    n = len(tokens)
    nodes = 0

    def parse_one() -> Sexp:
        nonlocal idx, nodes
        if idx >= n:
            raise ValueError("EOF")
        t = tokens[idx]
        if t != "(":
            idx += 1
            nodes += 1
            if nodes > max_nodes:
                raise ValueError("too many nodes")
            return t
        idx += 1  # consume '('
        lst: List[Sexp] = []
        while idx < n and tokens[idx] != ")":
            lst.append(parse_one())
        if idx >= n or tokens[idx] != ")":
            raise ValueError("unbalanced")
        idx += 1  # consume ')'
        nodes += 1
        if nodes > max_nodes:
            raise ValueError("too many nodes")
        return lst

    out: List[Sexp] = []
    while idx < n:
        t = tokens[idx]
        if t == ")":
            raise ValueError("unexpected )")
        out.append(parse_one())
    return out


def _iter_cil_sexps_from_tar(src_path: str, limit_files: int = 200, limit_total_bytes: int = 3_000_000) -> Iterable[Sexp]:
    total = 0
    cnt = 0
    for _, txt in _read_tar_members_text(src_path, (".cil", ".te", ".if", ".spt", ".conf", ".txt"), max_bytes=800_000):
        cnt += 1
        if cnt > limit_files:
            break
        if total > limit_total_bytes:
            break
        total += len(txt)
        try:
            toks = _tokenize_cil(txt)
            sexps = _parse_sexps(toks, max_nodes=50000)
        except Exception:
            continue
        for s in sexps:
            yield s


def _atom(s: Sexp) -> Optional[str]:
    return s if isinstance(s, str) else None


def _find_c_function_body_in_tar(src_path: str, func_name: str, max_scan_files: int = 600) -> Optional[str]:
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\([^;{]*\)\s*\{", re.MULTILINE)
    scanned = 0
    for _, txt in _read_tar_members_text(src_path, (".c", ".h"), max_bytes=3_000_000):
        scanned += 1
        if scanned > max_scan_files:
            break
        m = pat.search(txt)
        if not m:
            continue
        start = m.end() - 1  # points at '{'
        i = start
        depth = 0
        n = len(txt)
        while i < n:
            if txt[i] == "{":
                depth += 1
            elif txt[i] == "}":
                depth -= 1
                if depth == 0:
                    return txt[start + 1 : i]
            i += 1
        return txt[start + 1 :]
    return None


def _infer_call_args_style(src_path: str, keywords: Set[str]) -> str:
    # Returns "none" (no call keyword), "flat" (args follow directly), "list" (3rd arg is a list of args)
    if "call" not in keywords:
        return "none"

    # Try examples first
    styles = {"flat": 0, "list": 0}
    for sx in _iter_cil_sexps_from_tar(src_path):
        if not isinstance(sx, list) or not sx:
            continue
        if _atom(sx[0]) != "call":
            continue
        if len(sx) >= 3 and isinstance(sx[2], list) and len(sx) == 3:
            styles["list"] += 1
        elif len(sx) >= 3:
            styles["flat"] += 1
    if styles["flat"] or styles["list"]:
        return "list" if styles["list"] >= styles["flat"] else "flat"

    # Fall back to C parsing heuristics
    body = _find_c_function_body_in_tar(src_path, "cil_gen_call")
    if body:
        if ("->head" in body and "CIL_LIST" in body) or re.search(r"\bargs\b.*next->next", body) and ("CIL_LIST" in body):
            return "list"
        if re.search(r"curr\s*=\s*curr->next->next", body) and re.search(r"curr\s*=\s*curr->next", body):
            return "flat"
    return "flat"


def _infer_macro_param_style(src_path: str, keywords: Set[str]) -> Tuple[bool, str]:
    # Returns (untyped_allowed, order) where order in {"type-first","name-first","untyped"}
    untyped = 0
    typed_type_first = 0
    typed_name_first = 0

    for sx in _iter_cil_sexps_from_tar(src_path):
        if not isinstance(sx, list) or len(sx) < 3:
            continue
        if _atom(sx[0]) != "macro":
            continue
        params = sx[2]
        if not isinstance(params, list):
            continue
        for p in params:
            if not isinstance(p, list):
                continue
            if len(p) == 1 and _atom(p[0]) is not None:
                untyped += 1
            elif len(p) == 2 and _atom(p[0]) is not None and _atom(p[1]) is not None:
                a = _atom(p[0])
                b = _atom(p[1])
                if a in keywords and b not in keywords:
                    typed_type_first += 1
                elif b in keywords and a not in keywords:
                    typed_name_first += 1

    if untyped > 0:
        return True, "untyped"
    if typed_type_first or typed_name_first:
        return False, "type-first" if typed_type_first >= typed_name_first else "name-first"

    # Fallback: assume typed, type-first (common in CIL)
    return False, "type-first"


def _infer_classpermissionset_members_style(src_path: str, keywords: Set[str]) -> str:
    # Returns "list" (3rd arg is list-of-members) or "sibling" (members are subsequent args)
    # Examples first
    sibling = 0
    lst = 0
    for sx in _iter_cil_sexps_from_tar(src_path):
        if not isinstance(sx, list) or len(sx) < 3:
            continue
        if _atom(sx[0]) != "classpermissionset":
            continue
        if len(sx) > 3:
            sibling += 1
        elif len(sx) == 3 and isinstance(sx[2], list):
            # ambiguous; treat as list-style only if looks like list of atoms
            if all(isinstance(e, str) for e in sx[2]):
                lst += 1
    if sibling or lst:
        return "sibling" if sibling >= lst else "list"

    # C parsing heuristics
    body = _find_c_function_body_in_tar(src_path, "cil_gen_classpermissionset")
    if body:
        if "->head" in body and "CIL_LIST" in body:
            return "list"
        if re.search(r"curr\s*=\s*curr->next->next", body) and re.search(r"curr\s*=\s*curr->next", body):
            return "sibling"

    # Default: sibling (common for classperms-like constructs)
    return "sibling"


def _choose_param_type(keywords: Set[str]) -> str:
    # Prefer classpermission-related if available; else use a very common type keyword.
    for t in ("classpermission", "classperms", "classpermsset", "classpermissionset", "type", "string"):
        if t in keywords:
            return t
    return "type"


class Solution:
    def solve(self, src_path: str) -> bytes:
        keywords = _extract_keywords_from_source(src_path)

        call_style = _infer_call_args_style(src_path, keywords)  # none/flat/list
        untyped_allowed, param_order = _infer_macro_param_style(src_path, keywords)
        cps_members_style = _infer_classpermissionset_members_style(src_path, keywords)

        # Build macro parameter spec
        if untyped_allowed or param_order == "untyped":
            params = "((cp))"
        else:
            ptype = _choose_param_type(keywords)
            if param_order == "name-first":
                params = f"((cp {ptype}))"
            else:
                params = f"(({ptype} cp))"

        # Anonymous classpermission/classperms argument
        # If there is an explicit keyword, use it; otherwise pass raw classperms list.
        if "classpermission" in keywords:
            arg = "(classpermission (c (p)))"
        else:
            arg = "(c (p))"

        # classpermissionset member insertion depends on grammar
        if cps_members_style == "list":
            cps_stmt = "(classpermissionset s (cp))"
        else:
            cps_stmt = "(classpermissionset s cp)"

        # macro call
        if call_style == "none":
            call_stmt = f"(m {arg})"
        elif call_style == "list":
            call_stmt = f"(call m ({arg}))"
        else:
            call_stmt = f"(call m {arg})"

        cil = f"(class c (p))\n(macro m {params}\n {cps_stmt}\n)\n{call_stmt}\n"
        return cil.encode("utf-8")