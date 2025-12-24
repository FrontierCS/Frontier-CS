class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"foo 80 proto|" + b"A" * 43
