import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        base = b"1.1.1.1/1"
        target_len = 56
        if len(base) >= target_len:
            return base[:target_len]
        return base + b"A" * (target_len - len(base))