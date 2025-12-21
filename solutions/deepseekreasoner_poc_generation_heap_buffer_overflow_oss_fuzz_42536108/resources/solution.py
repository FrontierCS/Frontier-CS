class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x00' * 42 + b'\xFF\xFF\xFF\xFF'
