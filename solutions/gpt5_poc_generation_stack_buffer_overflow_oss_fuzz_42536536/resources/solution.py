from typing import *

class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"xref\n0 1\n" + (b"0" * 35) + b" 0 n\n"
