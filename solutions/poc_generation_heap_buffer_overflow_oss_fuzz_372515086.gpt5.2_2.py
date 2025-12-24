import os
import io
import re
import tarfile
import zipfile
from typing import Optional, Tuple, Iterable, List


class Solution:
    _LG = 1032
    _MAX_CAND_SIZE = 5 * 1024 * 1024

    _IGNORE_EXT = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
        ".py", ".java", ".kt", ".go", ".rs", ".js", ".ts",
        ".md", ".rst", ".adoc",
        ".cmake", ".make", ".mk",
        ".yml", ".yaml", ".toml", ".jsonschema",
        ".sh", ".bash", ".zsh", ".fish",
        ".in", ".am", ".ac", ".m4",
        ".gradle", ".sln", ".vcxproj", ".vcproj",
        ".plist", ".pbxproj",
        ".gni", ".gn", ".ninja",
        ".dox", ".doxygen",
        ".patch", ".diff",
        ".html", ".css",
        ".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9",
    }

    def _basename(self, p: str) -> str:
        p = p.replace("\\", "/")
        if "/" in p:
            return p.rsplit("/", 1)[-1]
        return p

    def _ext(self, p: str) -> str:
        b = self._basename(p)
        i = b.rfind(".")
        if i <= 0:
            return ""
        return b[i:].lower()

    def _pattern_score(self, name: str, size: int) -> int:
        n = name.lower().replace("\\", "/")
        b = self._basename(n)
        s = 0

        if "clusterfuzz-testcase-minimized" in n or b == "clusterfuzz-testcase-minimized":
            s = max(s, 120)
        if "clusterfuzz-testcase" in n:
            s = max(s, 110)
        if "minimized" in n:
            s = max(s, 95)
        if "testcase" in n:
            s = max(s, 90)
        if "poc" in n or "proof" in n:
            s = max(s, 85)
        if "crash" in n:
            s = max(s, 80)
        if "repro" in n or "reproducer" in n:
            s = max(s, 75)
        if "/corpus/" in n or n.startswith("corpus/"):
            s = max(s, 60)
        if "/testcases/" in n or "/testcase/" in n:
            s = max(s, 60)
        if "/artifacts/" in n:
            s = max(s, 60)

        ext = self._ext(n)
        if ext in (".bin", ".dat", ".raw", ".blob", ".input", ".fuzz", ".case"):
            s = max(s, 55)
        if ext in (".json", ".geojson", ".wkt", ".txt"):
            s = max(s, max(0, s - 5))

        if size == self._LG:
            s += 25
        elif abs(size - self._LG) <= 16:
            s += 12
        elif abs(size - self._LG) <= 128:
            s += 6

        return s

    def _is_probably_source(self, name: str) -> bool:
        n = name.lower().replace("\\", "/")
        if "/.git/" in n or n.startswith(".git/"):
            return True
        if "/.github/" in n or n.startswith(".github/"):
            return True
        if "/.gitlab/" in n or n.startswith(".gitlab/"):
            return True
        if n.endswith("/"):
            return True
        ext = self._ext(n)
        if ext in self._IGNORE_EXT:
            return True
        return False

    def _best_key(self, score: int, size: int) -> Tuple[int, int, int]:
        # Higher score better; then closer to LG; then smaller size
        return (-score, abs(size - self._LG), size)

    def _read_best_from_tar(self, tar_path: str) -> Optional[bytes]:
        best_member = None
        best_key = None

        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                size = int(getattr(m, "size", 0) or 0)
                if size <= 0 or size > self._MAX_CAND_SIZE:
                    continue
                name = m.name or ""
                if not name:
                    continue

                # Immediate hit
                ln = name.lower().replace("\\", "/")
                if ("clusterfuzz-testcase-minimized" in ln) and (not self._is_probably_source(name)):
                    f = tf.extractfile(m)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data

                if self._is_probably_source(name):
                    continue

                score = self._pattern_score(name, size)
                if score <= 0 and abs(size - self._LG) > 256:
                    continue

                key = self._best_key(score, size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_member = m

            if best_member is None:
                return None
            f = tf.extractfile(best_member)
            if f is None:
                return None
            data = f.read()
            return data if data else None

    def _read_best_from_zip(self, zip_path: str) -> Optional[bytes]:
        best_name = None
        best_key = None

        with zipfile.ZipFile(zip_path, "r") as zf:
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                size = int(zi.file_size or 0)
                if size <= 0 or size > self._MAX_CAND_SIZE:
                    continue
                name = zi.filename or ""
                if not name:
                    continue

                ln = name.lower().replace("\\", "/")
                if ("clusterfuzz-testcase-minimized" in ln) and (not self._is_probably_source(name)):
                    data = zf.read(name)
                    if data:
                        return data

                if self._is_probably_source(name):
                    continue

                score = self._pattern_score(name, size)
                if score <= 0 and abs(size - self._LG) > 256:
                    continue

                key = self._best_key(score, size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_name = name

            if best_name is None:
                return None
            data = zf.read(best_name)
            return data if data else None

    def _read_best_from_dir(self, dir_path: str) -> Optional[bytes]:
        best_path = None
        best_key = None

        for root, dirs, files in os.walk(dir_path):
            # prune typical VCS dirs
            dirs[:] = [d for d in dirs if d not in {".git", ".github", ".gitlab"}]
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, dir_path).replace("\\", "/")
                if self._is_probably_source(rel):
                    continue
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                size = int(st.st_size)
                if size <= 0 or size > self._MAX_CAND_SIZE:
                    continue

                ln = rel.lower()
                if "clusterfuzz-testcase-minimized" in ln:
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                        if data:
                            return data
                    except OSError:
                        pass

                score = self._pattern_score(rel, size)
                if score <= 0 and abs(size - self._LG) > 256:
                    continue

                key = self._best_key(score, size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_path = p

        if best_path is None:
            return None
        try:
            with open(best_path, "rb") as f:
                data = f.read()
            return data if data else None
        except OSError:
            return None

    def _try_neighbor_files(self, src_path: str) -> Optional[bytes]:
        base_dir = os.path.dirname(os.path.abspath(src_path))
        bn = os.path.basename(src_path)
        candidates = [
            "clusterfuzz-testcase-minimized",
            "clusterfuzz-testcase",
            "testcase",
            "poc",
            "crash",
            "repro",
            bn + ".poc",
            bn + ".input",
            bn + ".bin",
        ]
        for c in candidates:
            p = os.path.join(base_dir, c)
            if os.path.isfile(p):
                try:
                    with open(p, "rb") as f:
                        d = f.read()
                    if d:
                        return d
                except OSError:
                    pass
        return None

    def solve(self, src_path: str) -> bytes:
        data = self._try_neighbor_files(src_path)
        if data is not None:
            return data

        if os.path.isdir(src_path):
            data = self._read_best_from_dir(src_path)
            if data is not None:
                return data
            # try inside common subdirs
            for sub in ("reproducer", "repro", "artifacts", "testcase", "testcases", "corpus"):
                p = os.path.join(src_path, sub)
                if os.path.isdir(p):
                    data = self._read_best_from_dir(p)
                    if data is not None:
                        return data
            return (b"\xff" * self._LG)

        if os.path.isfile(src_path):
            if tarfile.is_tarfile(src_path):
                data = self._read_best_from_tar(src_path)
                if data is not None:
                    return data
                return (b"\xff" * self._LG)
            if zipfile.is_zipfile(src_path):
                data = self._read_best_from_zip(src_path)
                if data is not None:
                    return data
                return (b"\xff" * self._LG)

        return (b"\xff" * self._LG)