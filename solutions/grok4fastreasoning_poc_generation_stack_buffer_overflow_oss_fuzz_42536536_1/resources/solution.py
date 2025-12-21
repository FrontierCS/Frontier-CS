class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b'%PDF-1.4\nxref\n0 1\n'
        zeros = b'0' * 31
        return prefix + zeros
