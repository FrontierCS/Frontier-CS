import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.3\n"
        xref_section = (
            b"xref\n0 1\n"
            + (b"0" * 18)
            + b" "
            + (b"0" * 17)
            + b" n \n"
        )
        xref_offset = len(header)
        trailer = (
            b"trailer\n"
            b"<<>>\n"
            b"startxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )
        return header + xref_section + trailer