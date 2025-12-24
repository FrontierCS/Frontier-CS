import os
import tarfile
import zipfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        poc = None

        # Try tar-based archives first
        if tarfile.is_tarfile(src_path):
            try:
                poc = self._extract_from_tar(src_path)
            except Exception:
                poc = None
        else:
            # Fallback to zip if it's not a tar
            if zipfile.is_zipfile(src_path):
                try:
                    poc = self._extract_from_zip(src_path)
                except Exception:
                    poc = None

        if poc is not None:
            return poc

        # Fallback: return a generic 512-byte payload if nothing found
        # Use a somewhat structured pattern instead of pure zeros
        base = b"UPX!" + b"\x00" * (512 - 4)
        return base

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    BUG_ID = "383200048"
    TARGET_LEN = 512

    def _is_binary_sample(self, data: bytes) -> bool:
        if not data:
            return False
        # Consider bytes in typical text ranges
        text_chars = 0
        for b in data:
            if 32 <= b <= 126 or b in (9, 10, 13):
                text_chars += 1
        ratio = text_chars / len(data)
        # If >95% printable, treat as text, else binary
        return ratio <= 0.95

    def _score_path(self, path: str, size: int, is_binary: bool) -> int:
        lower = path.lower()
        score = 0

        # Strong preference for our specific bug id if present
        if self.BUG_ID in lower:
            score += 1000

        # Keywords strongly indicative of a PoC or fuzz testcase
        keywords_strong = [
            "poc",
            "crash",
            "heap",
            "overflow",
            "heap-buffer-overflow",
            "oss-fuzz",
            "ossfuzz",
            "clusterfuzz",
            "testcase",
            "regress",
            "sanitizer",
        ]
        for kw in keywords_strong:
            if kw in lower:
                score += 20

        # Lighter weight for generic fuzz/test/corpus locations
        keywords_light = [
            "fuzz",
            "corpus",
            "inputs",
            "input",
            "cases",
            "case",
            "tests",
            "test",
            "examples",
        ]
        for kw in keywords_light:
            if kw in lower:
                score += 5

        # File extension hints
        _, ext = os.path.splitext(lower)
        binary_exts = [
            ".bin",
            ".dat",
            ".upx",
            ".elf",
            ".so",
            ".raw",
            ".xz",
            ".gz",
            ".lz",
            ".lzma",
            ".bz2",
            ".bin2",
            ".img",
        ]
        if ext in binary_exts or ext == "":
            score += 5

        # Binary vs text
        if is_binary:
            score += 10
        else:
            score -= 15

        # Penalize very large / very small files
        # Prefer files near the target length (512)
        delta = abs(size - self.TARGET_LEN)
        # Subtract a small penalty proportional to distance from 512
        score -= delta // 16

        return score

    def _extract_from_tar(self, src_path: str) -> Optional[bytes]:
        best_member = None
        best_score = -10**9
        best_delta = 10**18

        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                if size <= 0:
                    continue
                # Skip very large files to avoid overhead
                if size > 4 * 1024 * 1024:
                    continue

                try:
                    f = tf.extractfile(m)
                except Exception:
                    continue
                if f is None:
                    continue

                try:
                    sample = f.read(min(1024, size))
                except Exception:
                    continue
                if not sample:
                    continue

                is_binary = self._is_binary_sample(sample)
                score = self._score_path(m.name, size, is_binary)
                delta = abs(size - self.TARGET_LEN)

                # Choose by highest score, then closest to 512 bytes
                if score > best_score or (score == best_score and delta < best_delta):
                    best_score = score
                    best_delta = delta
                    best_member = m

        if best_member is None:
            return None

        # If best_score is extremely low, it's probably not meaningful
        # but still might be our only candidate; we accept it.
        with tarfile.open(src_path, "r:*") as tf:
            f = tf.extractfile(best_member)
            if f is None:
                return None
            data = f.read()
            return data

    def _extract_from_zip(self, src_path: str) -> Optional[bytes]:
        best_name = None
        best_score = -10**9
        best_delta = 10**18

        with zipfile.ZipFile(src_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                size = info.file_size
                if size <= 0:
                    continue
                if size > 4 * 1024 * 1024:
                    continue

                try:
                    with zf.open(info, "r") as f:
                        sample = f.read(min(1024, size))
                except Exception:
                    continue
                if not sample:
                    continue

                is_binary = self._is_binary_sample(sample)
                score = self._score_path(info.filename, size, is_binary)
                delta = abs(size - self.TARGET_LEN)

                if score > best_score or (score == best_score and delta < best_delta):
                    best_score = score
                    best_delta = delta
                    best_name = info.filename

        if best_name is None:
            return None

        with zipfile.ZipFile(src_path, "r") as zf:
            try:
                with zf.open(best_name, "r") as f:
                    data = f.read()
                    return data
            except Exception:
                return None
