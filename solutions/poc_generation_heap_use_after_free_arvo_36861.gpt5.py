import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        prefix = b'usbredir' * 1024  # 8 KiB
        body = bytes(range(256)) * 320  # 80 KiB
        return prefix + body
