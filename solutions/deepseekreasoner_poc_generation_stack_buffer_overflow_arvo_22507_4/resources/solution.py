class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"%" + b"0" * 18 + b"d" + b"x" * 21
