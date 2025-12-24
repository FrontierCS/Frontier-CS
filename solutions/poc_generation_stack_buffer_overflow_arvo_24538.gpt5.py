import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x65GNU\x02' + b'A' * 22
