import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', 0, 0, 8, 2, 0, 0, 0)
        ihdr_chunk = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', 0xAE426082)
        return sig + ihdr_chunk + iend_chunk
