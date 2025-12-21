import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return ("a='" + ("a" * 68) + "'; a/=0;").encode("ascii")
