class Solution:
    def solve(self, src_path: str) -> bytes:
        return b"""(class c (p))
(classorder (c))
(macro m ((classpermission n)) (classpermissionset n (c (p))))
(call m ((c (p))))
"""