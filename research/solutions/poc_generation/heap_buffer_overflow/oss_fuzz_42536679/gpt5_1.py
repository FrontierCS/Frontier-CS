import struct
import binascii
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)
            return length + chunk_type + data + crc

        # PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"

        # IHDR: width=1, height=0, bit depth=8, color type=6 (RGBA), compression=0, filter=0, interlace=0
        width = 1
        height = 0
        ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        ihdr = png_chunk(b'IHDR', ihdr_data)

        # IDAT: one "row" worth of data even though height=0
        # Filter byte (0) + RGBA pixel (4 bytes)
        decompressed = bytes([0, 0, 0, 0, 0])
        idat_data = zlib.compress(decompressed)
        idat = png_chunk(b'IDAT', idat_data)

        # IEND
        iend = png_chunk(b'IEND', b'')

        return png_sig + ihdr + idat + iend