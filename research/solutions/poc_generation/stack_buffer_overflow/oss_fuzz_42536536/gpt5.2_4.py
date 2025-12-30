import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return (
            b"%PDF-1.0\n"
            b"xref\n0 1\n"
            b"00000000000 65535 f \n"
            b"startxref\n9\n%%EOF"
        )