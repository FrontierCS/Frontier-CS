class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "1000000000000000000 1000000000000000000\n"
        return poc.encode('ascii')