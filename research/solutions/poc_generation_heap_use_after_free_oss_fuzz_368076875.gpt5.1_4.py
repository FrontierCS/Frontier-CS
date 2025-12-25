import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        k = 140000
        s = "[" + "1," * (k - 1) + "1]"
        return s.encode("ascii")
