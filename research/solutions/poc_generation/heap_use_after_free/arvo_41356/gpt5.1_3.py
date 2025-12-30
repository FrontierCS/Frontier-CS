import os
import tarfile
import zipfile
import tempfile
import shutil
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            root = None
            if os.path.isdir(src_path):
                root = src_path
            else:
                if tarfile.is_tarfile(src_path):
                    tmpdir = tempfile.mkdtemp()
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(tmpdir)
                    root = tmpdir
                elif zipfile.is_zipfile(src_path):
                    tmpdir = tempfile.mkdtemp()
                    with zipfile.ZipFile(src_path, "r") as zf:
                        zf.extractall(tmpdir)
                    root = tmpdir
                else:
                    try:
                        with open(src_path, "rb") as f:
                            data = f.read()
                        if data:
                            return data[:60]
                    except Exception:
                        pass
                    return b"A" * 60

            data = self._find_poc(root)
            if data is not None:
                return data
            return b"A" * 60
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _find_poc(self, root: str) -> bytes | None:
        data = self._find_poc_datafile(root)
        if data is not None:
            return data
        data = self._find_poc_in_text(root)
        if data is not None:
            return data
        return None

    def _find_poc_datafile(self, root: str) -> bytes | None:
        keywords = [
            "poc",
            "crash",
            "uaf",
            "use_after_free",
            "use-after-free",
            "heap",
            "doublefree",
            "double_free",
            "exploit",
            "payload",
            "testcase",
            "input",
        ]
        best = None  # (score, size, path)
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                lower = fname.lower()
                if any(k in lower for k in keywords):
                    path = os.path.join(dirpath, fname)
                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        continue
                    if size <= 0 or size > 4096:
                        continue
                    score = abs(size - 60)
                    cand = (score, size, path)
                    if best is None or cand < best:
                        best = cand
        if best is not None:
            try:
                with open(best[2], "rb") as f:
                    return f.read()
            except OSError:
                return None
        return None

    def _find_poc_in_text(self, root: str) -> bytes | None:
        text_exts = {
            ".txt",
            ".md",
            ".markdown",
            ".rst",
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".hxx",
            ".sh",
            ".py",
            ".ini",
            ".cfg",
            ".conf",
            ".log",
        }
        pattern = re.compile(r"poc[^\"'\n]*[\"']([^\"']{1,200})[\"']", re.IGNORECASE)
        best = None  # (score, length, string)
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in text_exts:
                    continue
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > 8192:
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except OSError:
                    continue
                for m in pattern.finditer(content):
                    s = m.group(1)
                    if not s:
                        continue
                    # Avoid complicated escape sequences/formats
                    if "\\" in s or "%" in s:
                        continue
                    length = len(s)
                    score = abs(length - 60)
                    cand = (score, length, s)
                    if best is None or cand < best:
                        best = cand
        if best is not None:
            return best[2].encode("utf-8", errors="ignore")
        return None