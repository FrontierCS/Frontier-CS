import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal valid gzip stream containing an empty DEFLATE block (fixed Huffman).
        header = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff"
        deflate_empty_fixed = b"\x03\x00"
        footer_crc32_isize = struct.pack("<II", 0, 0)
        return header + deflate_empty_fixed + footer_crc32_isize