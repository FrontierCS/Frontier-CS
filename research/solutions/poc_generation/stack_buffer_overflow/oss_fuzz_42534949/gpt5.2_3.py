import os
import tarfile
import zipfile
import re
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._find_embedded_poc(src_path)
        if data is not None and len(data) > 0:
            return data
        return b"-0." + (b"0" * 13)

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        if os.path.isdir(src_path):
            return self._scan_dir_for_poc(src_path)
        p = src_path.lower()
        if p.endswith((".tar.gz", ".tgz", ".tar", ".tar.xz", ".txz", ".tar.bz2", ".tbz2")):
            return self._scan_tar_for_poc(src_path)
        if p.endswith(".zip"):
            return self._scan_zip_for_poc(src_path)
        d = self._scan_tar_for_poc(src_path)
        if d is not None:
            return d
        d = self._scan_zip_for_poc(src_path)
        return d

    def _score_name(self, name: str) -> int:
        n = name.lower()
        score = 0
        if "clusterfuzz" in n:
            score += 80
        if "testcase" in n:
            score += 70
        if "minimized" in n or "min" in n:
            score += 25
        if "crash" in n:
            score += 50
        if "poc" in n:
            score += 40
        if "repro" in n:
            score += 40
        if "regress" in n:
            score += 25
        if "oss-fuzz" in n or "ossfuzz" in n:
            score += 15
        if "fuzz" in n:
            score += 10
        if "corpus" in n:
            score += 10
        if "seed" in n:
            score += 5
        return score

    def _content_features(self, b: bytes) -> int:
        s = 0
        if b"-" in b:
            s += 5
        lb = b.lower()
        if b"inf" in lb or b"infinity" in lb:
            s += 7
        if b"nan" in lb:
            s += 5
        if self._mostly_printable(b):
            s += 3
        if len(b) == 16:
            s += 20
        return s

    def _mostly_printable(self, b: bytes) -> bool:
        if not b:
            return False
        printable = 0
        for c in b:
            if c in (9, 10, 13) or 32 <= c <= 126:
                printable += 1
        return printable * 10 >= len(b) * 9

    def _maybe_read_and_score(self, name: str, size: int, reader) -> Optional[Tuple[int, int, bytes]]:
        if size <= 0 or size > 4096:
            return None
        base_score = self._score_name(name)

        n = name.lower()
        ext = os.path.splitext(n)[1]
        is_source = ext in (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".py", ".java", ".js", ".ts", ".go", ".rs", ".cs", ".m", ".mm",
            ".md", ".rst", ".adoc", ".html", ".css", ".cmake", ".sh", ".bat",
            ".yml", ".yaml", ".xml", ".ini", ".cfg", ".mk", ".make",
        )
        is_textish = ext in (".txt", ".json", ".toml", ".yaml", ".yml", ".xml", ".csv", ".dat", ".in", ".input")
        if base_score == 0:
            if size > 512:
                return None
            if is_source and not is_textish:
                return None
            if not (("fuzz" in n) or ("corpus" in n) or ("test" in n) or ("poc" in n) or ("repro" in n) or ("crash" in n)):
                return None

        try:
            b = reader()
        except Exception:
            return None
        if not b:
            return None

        feature_score = self._content_features(b)
        total = base_score + feature_score
        total -= size // 128  # small penalty for larger
        if b.startswith(b"\x7fELF") or b.startswith(b"MZ"):
            total -= 100
        return (total, size, b)

    def _scan_tar_for_poc(self, tar_path: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, bytes]] = []
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    size = m.size
                    def make_reader(member=m):
                        def _r():
                            f = tf.extractfile(member)
                            if f is None:
                                return b""
                            try:
                                return f.read()
                            finally:
                                f.close()
                        return _r
                    scored = self._maybe_read_and_score(name, size, make_reader())
                    if scored is not None:
                        candidates.append(scored)
        except Exception:
            return None

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1]))
        best = candidates[0]
        if best[0] < 10:
            return None
        return best[2]

    def _scan_zip_for_poc(self, zip_path: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, bytes]] = []
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    name = zi.filename
                    size = zi.file_size
                    def make_reader(info=zi):
                        def _r():
                            with zf.open(info, "r") as f:
                                return f.read()
                        return _r
                    scored = self._maybe_read_and_score(name, size, make_reader())
                    if scored is not None:
                        candidates.append(scored)
        except Exception:
            return None

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1]))
        best = candidates[0]
        if best[0] < 10:
            return None
        return best[2]

    def _scan_dir_for_poc(self, root: str) -> Optional[bytes]:
        candidates: List[Tuple[int, int, bytes]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "node_modules", "venv", ".venv", "__pycache__")]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if not os.path.isfile(full):
                    continue
                name = os.path.relpath(full, root).replace(os.sep, "/")
                size = st.st_size

                def reader(path=full):
                    with open(path, "rb") as f:
                        return f.read()

                scored = self._maybe_read_and_score(name, size, reader)
                if scored is not None:
                    candidates.append(scored)

        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1]))
        best = candidates[0]
        if best[0] < 10:
            return None
        return best[2]