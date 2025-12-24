import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'.file 1 "a"\n.file 4294967289 "b"'