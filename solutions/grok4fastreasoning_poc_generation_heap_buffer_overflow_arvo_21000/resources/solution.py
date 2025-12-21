class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x00\x00\x00\x00\xff\xff' + b'\x00' * 27
