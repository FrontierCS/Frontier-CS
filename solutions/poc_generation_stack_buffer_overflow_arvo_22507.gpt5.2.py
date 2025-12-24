import os
import re
import tarfile
from typing import Iterable, Optional


class Solution:
    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[str]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".cxx") or name.endswith(".hpp")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(1_000_000)
                    except Exception:
                        continue
                    if not data:
                        continue
                    yield data.decode("latin1", errors="ignore")
        except Exception:
            return

    def _iter_text_files_from_dir(self, dir_path: str) -> Iterable[str]:
        for root, _, files in os.walk(dir_path):
            for fn in files:
                lfn = fn.lower()
                if not (lfn.endswith(".c") or lfn.endswith(".h") or lfn.endswith(".cc") or lfn.endswith(".cpp") or lfn.endswith(".cxx") or lfn.endswith(".hpp")):
                    continue
                p = os.path.join(root, fn)
                try:
                    with open(p, "rb") as f:
                        data = f.read(1_000_000)
                except Exception:
                    continue
                if not data:
                    continue
                yield data.decode("latin1", errors="ignore")

    def _dot_separator_likely(self, sources: Iterable[str]) -> bool:
        sscanf_dot = re.compile(r'\bsscanf\s*\([^;]{0,400}?"[^"]*?\.[^"]*?"', re.S)
        fscanf_dot = re.compile(r'\bfscanf\s*\([^;]{0,400}?"[^"]*?\.[^"]*?"', re.S)
        strchr_dot = re.compile(r'\bstrchr\s*\(\s*[^,]{1,200},\s*\'.\'\s*\)', re.S)
        split_dot = re.compile(r'\b(strtok|strsep)\s*\(\s*[^,]{1,200},\s*"[^"]*?\.[^"]*?"\s*\)', re.S)

        score = 0
        for s in sources:
            if sscanf_dot.search(s) or fscanf_dot.search(s):
                score += 3
            if strchr_dot.search(s):
                score += 1
            if split_dot.search(s):
                score += 1
            if score >= 3:
                return True
        return False

    def solve(self, src_path: str) -> bytes:
        sources: Iterable[str]
        if os.path.isdir(src_path):
            sources = self._iter_text_files_from_dir(src_path)
        else:
            if tarfile.is_tarfile(src_path):
                sources = self._iter_text_files_from_tar(src_path)
            else:
                sources = []

        use_dot = False
        try:
            use_dot = self._dot_separator_likely(sources)
        except Exception:
            use_dot = False

        n = "9223372036854775807"
        if use_dot:
            return (n + "." + n + "\n").encode("ascii")
        return (n + " " + n + "\n").encode("ascii")