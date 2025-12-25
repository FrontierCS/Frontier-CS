class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x40\x01\x00\x00\xd4\x02' + b'A' * 15
