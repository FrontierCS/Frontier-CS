import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # 19 digits + '.' + 19 digits + '\n' = 40 bytes
        return b"9223372036854775807.9223372036854775807\n"