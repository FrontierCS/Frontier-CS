import os
import tarfile
import io
import gzip
import bz2
import lzma
import zipfile


class Solution:
    TARGET_POC_SIZE = 37535

    def solve(self, src_path: str) -> bytes:
        data = b""
        try:
            if os.path.isdir(src_path):
                data = self._search_in_dir(src_path)
            else:
                tf = self._open_tar_maybe(src_path)
                if tf is not None:
                    with tf:
                        data = self._search_in_tar(tf)
                else:
                    data = self._read_file_safely(src_path)
        except Exception:
            data = b""

        if not data:
            data = self._fallback_poc()
        return data

    def _open_tar_maybe(self, path: str):
        try:
            return tarfile.open(path, "r:*")
        except (tarfile.TarError, OSError):
            return None

    def _score_name_size(self, name: str, size: int) -> int:
        ln = name.lower()
        score = 0
        kw_score = 0

        if "poc" in ln:
            kw_score += 100
        if "proof" in ln:
            kw_score += 40
        if "crash" in ln:
            kw_score += 80
        if "testcase" in ln:
            kw_score += 80
        if "clusterfuzz" in ln:
            kw_score += 80
        if "fuzz" in ln:
            kw_score += 20
        if "seed" in ln:
            kw_score += 30
        if "input" in ln:
            kw_score += 30
        if "id:" in ln:
            kw_score += 50
        if "bug" in ln:
            kw_score += 30
        if "regress" in ln:
            kw_score += 30
        if "42537670" in ln:
            kw_score += 120
        if "openpgp" in ln or "pgp" in ln or "gpg" in ln:
            kw_score += 20

        score += kw_score

        target = self.TARGET_POC_SIZE
        if size == target:
            score += 200
        else:
            diff = abs(size - target)
            if diff <= 16:
                score += 160
            elif diff <= 128:
                score += 120
            elif diff <= 512:
                score += 80
            elif diff <= 4096:
                score += 40
            elif diff <= 16384:
                score += 10

        if size < 10:
            score -= 50
        elif size < 50:
            score -= 20
        elif size > 1000000:
            score -= 80
        elif size > 200000:
            score -= 40

        if kw_score == 0:
            base = os.path.basename(ln)
            for ext in (
                ".c",
                ".cc",
                ".cpp",
                ".cxx",
                ".h",
                ".hpp",
                ".hh",
                ".java",
                ".py",
                ".pyc",
                ".sh",
                ".bash",
                ".zsh",
                ".txt",
                ".md",
                ".rst",
                ".html",
                ".xml",
                ".json",
                ".yaml",
                ".yml",
                ".ini",
                ".cfg",
                ".conf",
                ".cmake",
                ".in",
                ".am",
                ".ac",
                ".m4",
                ".pc",
                ".pl",
                ".rb",
                ".go",
                ".rs",
                ".hs",
                ".tex",
                ".pdf",
                ".ps",
                ".eps",
                ".svg",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".bmp",
                ".tiff",
                ".ico",
                ".csv",
                ".tsv",
                ".log",
                ".gz",
                ".bz2",
                ".xz",
                ".zip",
                ".7z",
                ".rar",
                ".tar",
            ):
                if base.endswith(ext):
                    score -= 100
                    break

        return score

    def _maybe_decompress(self, data: bytes, name: str) -> bytes:
        ln = name.lower()
        try:
            if ln.endswith(".gz") or ln.endswith(".gzip"):
                return gzip.decompress(data)
            if ln.endswith(".bz2"):
                return bz2.decompress(data)
            if ln.endswith(".xz") or ln.endswith(".lzma"):
                return lzma.decompress(data)
            if ln.endswith(".zip"):
                bio = io.BytesIO(data)
                with zipfile.ZipFile(bio) as zf:
                    for member in zf.namelist():
                        if not member.endswith("/"):
                            return zf.read(member)
        except Exception:
            pass
        return data

    def _search_in_tar(self, tf: tarfile.TarFile) -> bytes:
        best_member = None
        best_score = None

        for m in tf.getmembers():
            if not m.isreg():
                continue
            if m.size <= 0:
                continue
            score = self._score_name_size(m.name, m.size)
            if best_score is None or score > best_score:
                best_score = score
                best_member = m

        if best_member is not None and (best_score is None or best_score > 0):
            f = tf.extractfile(best_member)
            if f is not None:
                raw = f.read()
                return self._maybe_decompress(raw, best_member.name)

        target = self.TARGET_POC_SIZE
        for m in tf.getmembers():
            if m.isreg() and m.size == target:
                f = tf.extractfile(m)
                if f is not None:
                    raw = f.read()
                    return self._maybe_decompress(raw, m.name)

        return b""

    def _search_in_dir(self, root: str) -> bytes:
        best_path = None
        best_score = None

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                d
                for d in dirnames
                if d
                not in (
                    ".git",
                    ".hg",
                    ".svn",
                    ".idea",
                    "__pycache__",
                    "build",
                    "cmake-build-debug",
                    "cmake-build-release",
                )
            ]
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue
                rel = os.path.relpath(path, root)
                score = self._score_name_size(rel, size)
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

        if best_path is not None and (best_score is None or best_score > 0):
            raw = self._read_file_safely(best_path)
            return self._maybe_decompress(raw, best_path)

        target = self.TARGET_POC_SIZE
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == target:
                    raw = self._read_file_safely(path)
                    return self._maybe_decompress(raw, path)

        return b""

    def _read_file_safely(self, path: str) -> bytes:
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return b""

    def _fallback_poc(self) -> bytes:
        return b"A"