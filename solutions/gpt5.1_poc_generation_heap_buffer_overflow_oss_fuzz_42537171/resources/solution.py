import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        size = 825339
        pattern = bytes(range(256))
        full_repeats, remainder = divmod(size, len(pattern))
        return pattern * full_repeats + pattern[:remainder]
