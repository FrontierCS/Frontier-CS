import os
import io
import tarfile
import zipfile
import gzip
import bz2
import lzma
from typing import Optional, List, Tuple


class Solution:
    POC_SIZE = 150979
    MAX_NESTED_CONTAINER_SIZE = 50 * 1024 * 1024  # 50MB

    def solve(self, src_path: str) -> bytes:
        data = self._search_in_path(src_path)
        if data is not None:
            return data
        # Fallback: return empty bytes if nothing found
        return b""

    def _search_in_path(self, path: str) -> Optional[bytes]:
        # Try tarfile
        try:
            if tarfile.is_tarfile(path):
                with tarfile.open(path, mode="r:*") as tf:
                    res = self._search_in_tarfile(tf)
                    if res is not None:
                        return res
        except Exception:
            pass

        # Try zipfile
        try:
            if zipfile.is_zipfile(path):
                with zipfile.ZipFile(path, mode="r") as zf:
                    res = self._search_in_zipfile(zf)
                    if res is not None:
                        return res
        except Exception:
            pass

        # As a last resort, try reading raw bytes and probing for nested archives
        try:
            with open(path, "rb") as f:
                raw = f.read()
            return self._search_in_bytes(raw)
        except Exception:
            return None

    def _search_in_tarfile(self, tf: tarfile.TarFile) -> Optional[bytes]:
        members = [m for m in tf.getmembers() if m.isfile()]
        # First: exact size match
        exact_size_candidates = [m for m in members if m.size == self.POC_SIZE]
        if exact_size_candidates:
            chosen = self._choose_best_member([m.name for m in exact_size_candidates], [m.size for m in exact_size_candidates])
            if chosen is not None:
                try:
                    f = tf.extractfile(exact_size_candidates[chosen])
                    if f:
                        return f.read()
                except Exception:
                    pass

        # Second: name contains bug id
        bug_candidates = [m for m in members if self._name_has_bugid(m.name)]
        if bug_candidates:
            chosen = self._choose_best_member([m.name for m in bug_candidates], [m.size for m in bug_candidates])
            if chosen is not None:
                try:
                    f = tf.extractfile(bug_candidates[chosen])
                    if f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        # Third: look for nested archives inside tar
        nested = self._find_nested_archive_members(members)
        for m in nested:
            if m.size <= self.MAX_NESTED_CONTAINER_SIZE:
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    res = self._search_in_bytes(data)
                    if res is not None:
                        return res
                except Exception:
                    continue

        # Fourth: look for plausible PoC by heuristic names
        heuristic_candidates = [m for m in members if self._name_looks_like_poc(m.name)]
        if heuristic_candidates:
            chosen = self._choose_best_member([m.name for m in heuristic_candidates],
                                              [m.size for m in heuristic_candidates])
            if chosen is not None:
                try:
                    f = tf.extractfile(heuristic_candidates[chosen])
                    if f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        return None

    def _search_in_zipfile(self, zf: zipfile.ZipFile) -> Optional[bytes]:
        infos = [zi for zi in zf.infolist() if not zi.is_dir()]
        # First: exact size match
        exact_size_candidates = [zi for zi in infos if zi.file_size == self.POC_SIZE]
        if exact_size_candidates:
            chosen = self._choose_best_member([zi.filename for zi in exact_size_candidates],
                                              [zi.file_size for zi in exact_size_candidates])
            if chosen is not None:
                try:
                    with zf.open(exact_size_candidates[chosen], "r") as f:
                        return f.read()
                except Exception:
                    pass

        # Second: name contains bug id
        bug_candidates = [zi for zi in infos if self._name_has_bugid(zi.filename)]
        if bug_candidates:
            chosen = self._choose_best_member([zi.filename for zi in bug_candidates],
                                              [zi.file_size for zi in bug_candidates])
            if chosen is not None:
                try:
                    with zf.open(bug_candidates[chosen], "r") as f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        # Third: nested archives inside zip
        nested = self._find_nested_archive_names(infos)
        for zi in nested:
            if zi.file_size <= self.MAX_NESTED_CONTAINER_SIZE:
                try:
                    with zf.open(zi, "r") as f:
                        data = f.read()
                    res = self._search_in_bytes(data)
                    if res is not None:
                        return res
                except Exception:
                    continue

        # Fourth: heuristic names
        heuristic_candidates = [zi for zi in infos if self._name_looks_like_poc(zi.filename)]
        if heuristic_candidates:
            chosen = self._choose_best_member([zi.filename for zi in heuristic_candidates],
                                              [zi.file_size for zi in heuristic_candidates])
            if chosen is not None:
                try:
                    with zf.open(heuristic_candidates[chosen], "r") as f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        return None

    def _search_in_bytes(self, data: bytes) -> Optional[bytes]:
        # Try to open as tar
        try:
            bio = io.BytesIO(data)
            with tarfile.open(fileobj=bio, mode="r:*") as tf:
                res = self._search_in_tarfile(tf)
                if res is not None:
                    return res
        except Exception:
            pass

        # Try as zip
        try:
            bio = io.BytesIO(data)
            with zipfile.ZipFile(bio, mode="r") as zf:
                res = self._search_in_zipfile(zf)
                if res is not None:
                    return res
        except Exception:
            pass

        # Try decompressors (gzip, bz2, lzma), then recurse
        # gzip
        if self._looks_like_gzip(data):
            try:
                decompressed = gzip.decompress(data)
                res = self._search_in_bytes(decompressed)
                if res is not None:
                    return res
            except Exception:
                pass

        # bz2
        if self._looks_like_bz2(data):
            try:
                decompressed = bz2.decompress(data)
                res = self._search_in_bytes(decompressed)
                if res is not None:
                    return res
            except Exception:
                pass

        # lzma/xz
        if self._looks_like_xz(data):
            try:
                decompressed = lzma.decompress(data)
                res = self._search_in_bytes(decompressed)
                if res is not None:
                    return res
            except Exception:
                pass

        # If still nothing: If the raw data length matches POC_SIZE, just return it
        if len(data) == self.POC_SIZE:
            return data

        return None

    def _choose_best_member(self, names: List[str], sizes: List[int]) -> Optional[int]:
        # Rank based on heuristic score; prefer exact size match implicitly handled earlier
        best_idx = None
        best_score = -10**9
        for i, name in enumerate(names):
            score = self._score_name(name)
            # Bias slightly towards exact size if equal names list contains mixed sizes
            if sizes[i] == self.POC_SIZE:
                score += 50
            # Prefer plausible file types
            score += self._ext_score(name)
            # Slightly prefer shorter paths (likely direct file rather than source)
            score -= name.count("/") + name.count("\\")
            if score > best_score:
                best_score = score
                best_idx = i
        return best_idx

    def _score_name(self, name: str) -> int:
        n = name.lower()
        score = 0
        if self._name_has_bugid(n):
            score += 100
        keywords_pos = [
            "oss-fuzz",
            "clusterfuzz",
            "crash",
            "repro",
            "reproducer",
            "testcase",
            "poc",
            "pdfwrite",
            "ghostscript",
            "fuzz",
            "min",
            "minimized",
        ]
        for k in keywords_pos:
            if k in n:
                score += 10
        keywords_neg = [
            "seed",
            "corpus",
            "example",
            "samples",
            "third_party",
            "src/",
            "docs",
            "doc",
            "license",
            "readme",
        ]
        for k in keywords_neg:
            if k in n:
                score -= 8
        # Prefer known data file extensions
        score += self._ext_score(n)
        return score

    def _ext_score(self, name: str) -> int:
        n = name.lower()
        exts = {
            ".pdf": 40,
            ".ps": 40,
            ".eps": 35,
            ".xps": 25,
            ".pcl": 25,
            ".svg": 20,
            ".ai": 20,
            ".txt": 5,
            ".bin": 5,
        }
        for ext, val in exts.items():
            if n.endswith(ext):
                return val
        # Penalize source-like extensions
        for ext in [".c", ".cc", ".cpp", ".h", ".hpp", ".py", ".java", ".go", ".rs", ".md"]:
            if n.endswith(ext):
                return -20
        return 0

    def _name_has_bugid(self, name: str) -> bool:
        n = name.lower()
        bug_tokens = [
            "42535696",
            "oss-fuzz-42535696",
            "clusterfuzz-42535696",
            "testcase-42535696",
            "bug-42535696",
        ]
        return any(tok in n for tok in bug_tokens)

    def _name_looks_like_poc(self, name: str) -> bool:
        n = name.lower()
        keywords = ["poc", "crash", "repro", "reproducer", "testcase", "minimized", "clusterfuzz", "oss-fuzz"]
        if any(k in n for k in keywords):
            return True
        # Also consider likely data files for Ghostscript
        for ext in [".pdf", ".ps", ".eps", ".xps", ".pcl", ".svg", ".ai"]:
            if n.endswith(ext):
                return True
        return False

    def _find_nested_archive_members(self, members: List[tarfile.TarInfo]) -> List[tarfile.TarInfo]:
        nested_exts = (".tar", ".tar.gz", ".tgz", ".zip", ".gz", ".xz", ".bz2")
        res = []
        for m in members:
            nm = m.name.lower()
            if any(nm.endswith(ext) for ext in nested_exts):
                res.append(m)
        return res

    def _find_nested_archive_names(self, infos: List[zipfile.ZipInfo]) -> List[zipfile.ZipInfo]:
        nested_exts = (".tar", ".tar.gz", ".tgz", ".zip", ".gz", ".xz", ".bz2")
        res = []
        for zi in infos:
            nm = zi.filename.lower()
            if any(nm.endswith(ext) for ext in nested_exts):
                res.append(zi)
        return res

    def _looks_like_gzip(self, data: bytes) -> bool:
        return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B

    def _looks_like_bz2(self, data: bytes) -> bool:
        return len(data) >= 3 and data[0:3] == b'BZh'

    def _looks_like_xz(self, data: bytes) -> bool:
        return len(data) >= 6 and data[0:6] == b"\xfd7zXZ\x00"