import re
import tarfile
import os
from typing import Dict, List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        registry = b"Adobe"
        ordering = b"Identity"
        return self._build_pdf(registry, ordering)

    def _build_pdf(self, registry: bytes, ordering: bytes) -> bytes:
        stream = b"BT /F1 12 Tf 72 720 Td <0000> Tj ET"

        objects: Dict[int, bytes] = {}
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        objects[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 6 0 R >>"
        objects[4] = b"<< /Type /Font /Subtype /Type0 /BaseFont /F1 /Encoding /Identity-H /DescendantFonts [5 0 R] >>"

        cid_system_info = b"<< /Registry (" + registry + b") /Ordering (" + ordering + b") /Supplement 0 >>"
        objects[5] = b"<< /Type /Font /Subtype /CIDFontType2 /CIDSystemInfo " + cid_system_info + b" /FontDescriptor 7 0 R /W [0 [500]] /DW 500 /CIDToGIDMap /Identity >>"

        objects[6] = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        objects[7] = b"<< /Type /FontDescriptor /FontName /F1 /Flags 4 /FontBBox [0 0 0 0] /Ascent 0 /Descent 0 /CapHeight 0 /ItalicAngle 0 /StemV 0 >>"

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        out = bytearray(header)

        max_obj = max(objects.keys())
        offsets = [0] * (max_obj + 1)

        for n in range(1, max_obj + 1):
            offsets[n] = len(out)
            out += f"{n} 0 obj\n".encode("ascii")
            out += objects[n]
            out += b"\nendobj\n"

        xref_offset = len(out)
        out += f"xref\n0 {max_obj + 1}\n".encode("ascii")
        out += b"0000000000 65535 f \n"
        for n in range(1, max_obj + 1):
            out += f"{offsets[n]:010d} 00000 n \n".encode("ascii")

        out += b"trailer\n"
        out += f"<< /Size {max_obj + 1} /Root 1 0 R >>\n".encode("ascii")
        out += b"startxref\n"
        out += f"{xref_offset}\n".encode("ascii")
        out += b"%%EOF\n"
        return bytes(out)