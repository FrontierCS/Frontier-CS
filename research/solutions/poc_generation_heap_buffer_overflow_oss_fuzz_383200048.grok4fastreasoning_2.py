import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        header = struct.pack('<16sHHIQQQIHHHHHH', ident, 3, 0x3e, 1, 0, 0x40, 0, 0, 0x40, 0x38, 8, 0, 0, 0)
        ph_template = struct.pack('<8Q', 1, 5, 0, 0x400000, 0x400000, 100, 200, 0x1000)
        phs = ph_template * 8
        return header + phs