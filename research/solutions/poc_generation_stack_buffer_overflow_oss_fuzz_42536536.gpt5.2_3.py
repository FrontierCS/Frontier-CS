import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"xref\n0 1\n" + (b"0" * 29) + b" 00000 n0\n"