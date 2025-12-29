import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = zlib.crc32(chunk_type + data) & 0xffffffff
            crc_bytes = struct.pack(">I", crc)
            return length + chunk_type + data + crc_bytes

        def make_png_zero_width(height: int = 32) -> bytes:
            # PNG signature
            signature = b"\x89PNG\r\n\x1a\n"

            # IHDR with width=0, height=height, bit depth 8, color type 6 (RGBA), compression 0, filter 0, interlace 0
            ihdr_data = (
                struct.pack(">I", 0) +                 # Width = 0
                struct.pack(">I", height) +            # Height = height
                b"\x08" +                              # Bit depth = 8
                b"\x06" +                              # Color type = RGBA
                b"\x00" +                              # Compression method
                b"\x00" +                              # Filter method
                b"\x00"                                # Interlace method
            )
            ihdr_chunk = png_chunk(b'IHDR', ihdr_data)

            # IDAT: zlib-compressed data for 'height' filter bytes (one per scanline)
            # Using zeros as filter type 0 for each row
            raw_scanlines = b"\x00" * height
            idat_data = zlib.compress(raw_scanlines)
            idat_chunk = png_chunk(b'IDAT', idat_data)

            # IEND
            iend_chunk = png_chunk(b'IEND', b'')

            return signature + ihdr_chunk + idat_chunk + iend_chunk

        return make_png_zero_width(32)