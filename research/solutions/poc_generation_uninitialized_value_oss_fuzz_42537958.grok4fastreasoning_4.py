class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\xff\xd8' + b'\x00' * 2704 + b'\xff\xd9'