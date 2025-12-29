class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x16\x48\x00' + b'\x00' * 30