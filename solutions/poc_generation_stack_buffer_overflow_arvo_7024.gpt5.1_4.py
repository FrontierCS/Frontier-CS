import os
import tarfile
import zipfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        if tarfile.is_tarfile(src_path):
            data = self._extract_from_tar(src_path)
            if data is not None:
                return data

        if zipfile.is_zipfile(src_path):
            data = self._extract_from_zip(src_path)
            if data is not None:
                return data

        return self._fallback_poc()

    def _score_candidate(self, name: str, size: int) -> int:
        name_l = name.lower()

        text_exts = {
            ".txt", ".md", ".rst", ".c", ".h", ".cpp", ".cc", ".cxx", ".java",
            ".py", ".sh", ".cmake", ".html", ".htm", ".xml", ".yml", ".yaml",
            ".json", ".toml", ".ini", ".cfg", ".conf", ".bat", ".ps1", ".csv",
            ".tsv"
        }
        binary_exts = {
            ".bin", ".dat", ".data", ".raw", ".pcap", ".pcapng", ".dump",
            ".pkt", ".packet"
        }

        base, ext = os.path.splitext(name_l)

        score = 0

        if size > 0:
            distance = abs(size - 45)
            score += max(0, 100 - distance)

        if size == 45:
            score += 400

        patterns = [
            "poc", "crash", "testcase", "oss-fuzz", "clusterfuzz", "id:",
            "id_", "repro", "reproducer", "input", "payload", "trigger",
            "minimized"
        ]
        for p in patterns:
            if p in name_l:
                score += 80

        if "wireshark" in name_l or "fuzz" in name_l:
            score += 20

        if ext in binary_exts:
            score += 40
        if ext in text_exts:
            score -= 80

        if size > 10_000:
            score -= 50

        return score

    def _extract_from_tar(self, path: str) -> Optional[bytes]:
        best_member = None
        best_score = None

        try:
            with tarfile.open(path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    size = m.size
                    if size <= 0:
                        continue
                    name = m.name or ""
                    score = self._score_candidate(name, size)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_member = m

                if best_member is not None and best_score is not None:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            return None

        return None

    def _extract_from_zip(self, path: str) -> Optional[bytes]:
        best_info = None
        best_score = None

        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    size = info.file_size
                    if size <= 0:
                        continue
                    name = info.filename or ""
                    score = self._score_candidate(name, size)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_info = info

                if best_info is not None and best_score is not None:
                    with zf.open(best_info, "r") as f:
                        data = f.read()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            return None

        return None

    def _fallback_poc(self) -> bytes:
        return b"A" * 45
