import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.1\n"
        xref_offset = len(header)

        xref = b"xref\n0 1\n" + (b"0" * 20) + b"0\n"
        tail = b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
        return header + xref + tail