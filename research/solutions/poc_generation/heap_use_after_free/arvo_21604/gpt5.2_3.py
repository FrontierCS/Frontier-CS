import os
from typing import List, Tuple, Dict, Optional

class Solution:
    def _pdf_build(self, obj_contents: List[bytes], root_objnum: int = 1) -> bytes:
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        out = bytearray()
        out += header

        offsets = [0] * (len(obj_contents) + 1)  # 0th unused
        for i, content in enumerate(obj_contents, start=1):
            offsets[i] = len(out)
            out += str(i).encode("ascii") + b" 0 obj\n"
            out += content
            if not content.endswith(b"\n"):
                out += b"\n"
            out += b"endobj\n"

        xref_off = len(out)
        size = len(obj_contents) + 1
        out += b"xref\n"
        out += b"0 " + str(size).encode("ascii") + b"\n"
        out += b"0000000000 65535 f \n"
        for i in range(1, size):
            out += f"{offsets[i]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += b"<< /Size " + str(size).encode("ascii") + b" /Root " + str(root_objnum).encode("ascii") + b" 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_off).encode("ascii") + b"\n"
        out += b"%%EOF\n"
        return bytes(out)

    def solve(self, src_path: str) -> bytes:
        # Minimal PDF designed to create standalone (orphan) widget annotations while AcroForm exists.
        # This tends to exercise standalone form creation/destruction paths.
        catalog = b"<< /Type /Catalog /Pages 2 0 R /AcroForm 8 0 R >>\n"

        pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"

        page = (
            b"<< /Type /Page /Parent 2 0 R\n"
            b"/MediaBox [0 0 300 300]\n"
            b"/Resources << /Font << /Helv 9 0 R >> >>\n"
            b"/Annots [4 0 R 5 0 R 6 0 R]\n"
            b"/Contents 7 0 R\n"
            b">>\n"
        )

        def widget(name: bytes, rect: bytes) -> bytes:
            # Orphan widget: no /Parent and not in /AcroForm/Fields -> standalone form
            return (
                b"<< /Type /Annot /Subtype /Widget\n"
                b"/Rect " + rect + b"\n"
                b"/P 3 0 R\n"
                b"/FT /Tx\n"
                b"/T (" + name + b")\n"
                b"/V (" + name + b")\n"
                b"/F 4\n"
                b"/DA (/Helv 12 Tf 0 g)\n"
                b">>\n"
            )

        w1 = widget(b"A", b"[10 10 110 40]")
        w2 = widget(b"B", b"[10 60 110 90]")
        w3 = widget(b"C", b"[10 110 110 140]")

        contents = b"<< /Length 0 >>\nstream\n\nendstream\n"

        acroform = (
            b"<< /Fields []\n"
            b"/NeedAppearances true\n"
            b"/DR << /Font << /Helv 9 0 R >> >>\n"
            b"/DA (/Helv 12 Tf 0 g)\n"
            b">>\n"
        )

        helv_font = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"

        objs = [catalog, pages, page, w1, w2, w3, contents, acroform, helv_font]
        return self._pdf_build(objs, root_objnum=1)