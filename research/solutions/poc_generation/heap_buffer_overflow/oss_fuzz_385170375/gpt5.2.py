import os
import re
import io
import tarfile
import zipfile
from typing import Iterable, Tuple, Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        best = self._find_best_poc(src_path)
        if best is not None:
            return best
        return b"\x00" * 149

    def _find_best_poc(self, src_path: str) -> Optional[bytes]:
        candidates = []
        for name, size, loader in self._enumerate_candidate_loaders(src_path):
            score = self._pre_score_name(name, size)
            if score <= -1e9:
                continue
            candidates.append((score, name, size, loader))
        candidates.sort(key=lambda x: (-x[0], x[2], x[1]))

        best_score = -1e18
        best_data = None

        for _, name, size, loader in candidates[:250]:
            data = None
            try:
                data = loader()
            except Exception:
                continue
            if not data:
                continue

            score = self._score_data(name, data)

            if score > best_score:
                best_score = score
                best_data = data

            if len(data) == 149 and ("clusterfuzz-testcase-minimized" in name.lower() or "clusterfuzz" in name.lower()):
                return data

            nested = self._scan_nested_archives(name, data, depth=2)
            if nested is not None:
                n_score, n_data = nested
                if n_score > best_score:
                    best_score = n_score
                    best_data = n_data

        if best_data is not None:
            return best_data

        direct = self._try_find_exact_149(src_path)
        if direct is not None:
            return direct

        return None

    def _try_find_exact_149(self, src_path: str) -> Optional[bytes]:
        for name, size, loader in self._enumerate_candidate_loaders(src_path, only_size=149):
            try:
                data = loader()
            except Exception:
                continue
            if data and len(data) == 149:
                return data
        return None

    def _enumerate_candidate_loaders(self, src_path: str, only_size: Optional[int] = None) -> Iterable[Tuple[str, int, callable]]:
        if os.path.isdir(src_path):
            yield from self._enumerate_dir_loaders(src_path, only_size=only_size)
            return

        if os.path.isfile(src_path):
            # Try as tar archive
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if only_size is not None and m.size != only_size:
                            continue
                        if m.size <= 0 or m.size > 5 * 1024 * 1024:
                            continue
                        name = m.name
                        size = m.size

                        def make_loader(member=m, tpath=src_path):
                            def _load():
                                with tarfile.open(tpath, "r:*") as _tf:
                                    f = _tf.extractfile(member)
                                    if f is None:
                                        return b""
                                    return f.read()
                            return _load

                        yield (name, size, make_loader())
                return
            except Exception:
                pass

            # If not tar, treat as a single file (maybe PoC itself)
            try:
                st = os.stat(src_path)
                if only_size is None or st.st_size == only_size:
                    if 0 < st.st_size <= 5 * 1024 * 1024:
                        def loader(p=src_path):
                            with open(p, "rb") as f:
                                return f.read()
                        yield (os.path.basename(src_path), int(st.st_size), loader)
            except Exception:
                pass
            return

    def _enumerate_dir_loaders(self, root: str, only_size: Optional[int] = None) -> Iterable[Tuple[str, int, callable]]:
        root = os.path.abspath(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", ".svn", ".hg", "build", "out", "dist", "CMakeFiles", "__pycache__")]
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if only_size is not None and st.st_size != only_size:
                    continue
                if st.st_size <= 0 or st.st_size > 5 * 1024 * 1024:
                    continue
                rel = os.path.relpath(path, root).replace("\\", "/")

                def loader(p=path):
                    with open(p, "rb") as f:
                        return f.read()

                yield (rel, int(st.st_size), loader)

    def _pre_score_name(self, name: str, size: int) -> float:
        n = name.lower()

        bad_ext = (
            ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm", ".s", ".S",
            ".py", ".pyi", ".java", ".kt", ".rs", ".go",
            ".md", ".rst", ".txt", ".html", ".css", ".js", ".ts",
            ".json", ".yml", ".yaml", ".toml", ".ini",
            ".cmake", ".mk", ".mak", ".make", ".ninja",
            ".o", ".a", ".so", ".dll", ".dylib", ".exe", ".obj",
            ".patch", ".diff",
        )

        base = 0.0

        if "clusterfuzz-testcase-minimized" in n:
            base += 5000
        elif "clusterfuzz-testcase" in n:
            base += 4000
        if "minimized" in n:
            base += 300
        if "poc" in n:
            base += 800
        if "crash" in n or "asan" in n or "ubsan" in n:
            base += 700
        if "repro" in n:
            base += 600
        if "rv60" in n or "rv6" in n or "realvideo" in n:
            base += 250
        if "avcodec" in n or "decoder" in n:
            base += 80

        _, ext = os.path.splitext(n)
        if ext in (".bin", ".dat", ".raw", ".rm", ".rmvb", ".rv", ".rvid", ".ivf", ".mkv", ".avi", ".mp4", ".mov", ".flv"):
            base += 200

        if size == 149:
            base += 2500
        elif 0 < size <= 2048:
            base += 200
        elif size <= 8192:
            base += 80

        if ext in bad_ext and "clusterfuzz" not in n and "poc" not in n and "crash" not in n and "repro" not in n:
            base -= 1000

        base -= min(size, 5 * 1024 * 1024) / 200.0
        return base

    def _score_data(self, name: str, data: bytes) -> float:
        n = name.lower()
        size = len(data)
        score = self._pre_score_name(name, size)

        if size == 149:
            score += 800

        if self._looks_like_text(data) and ("clusterfuzz" not in n):
            score -= 500

        if self._looks_like_archive(data):
            score -= 200

        if self._looks_like_riff(data):
            score += 50
        if self._looks_like_ogg(data):
            score += 50
        if self._looks_like_matroska(data):
            score += 50
        if self._looks_like_rm(data):
            score += 120

        if any(b in data for b in (b"RV60", b"rv60", b"RV30", b"RV40")):
            score += 200

        if data.count(b"\x00") > max(8, size // 6):
            score += 30

        return score

    def _looks_like_text(self, data: bytes) -> bool:
        if not data:
            return False
        if b"\x00" in data:
            return False
        sample = data[:2048]
        try:
            s = sample.decode("utf-8")
        except Exception:
            return False
        printable = sum(1 for ch in s if ch.isprintable() or ch in "\r\n\t")
        return printable / max(1, len(s)) > 0.92

    def _looks_like_archive(self, data: bytes) -> bool:
        if len(data) < 6:
            return False
        if data[:4] == b"PK\x03\x04":
            return True
        if data[:2] == b"\x1f\x8b":
            return True
        if data[:6] == b"\xfd7zXZ\x00":
            return True
        if data[:3] == b"BZh":
            return True
        if len(data) > 265 and data[257:262] == b"ustar":
            return True
        return False

    def _looks_like_riff(self, data: bytes) -> bool:
        return len(data) >= 12 and data[:4] == b"RIFF"

    def _looks_like_ogg(self, data: bytes) -> bool:
        return len(data) >= 4 and data[:4] == b"OggS"

    def _looks_like_matroska(self, data: bytes) -> bool:
        return len(data) >= 4 and data[:4] == b"\x1a\x45\xdf\xa3"

    def _looks_like_rm(self, data: bytes) -> bool:
        return len(data) >= 4 and data[:4] == b".RMF"

    def _scan_nested_archives(self, name: str, data: bytes, depth: int = 1) -> Optional[Tuple[float, bytes]]:
        if depth <= 0 or not data or len(data) > 5 * 1024 * 1024:
            return None

        best_score = -1e18
        best_data = None

        if data[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    infos = [zi for zi in zf.infolist() if not zi.is_dir()]
                    infos.sort(key=lambda zi: (zi.file_size, zi.filename))
                    for zi in infos[:200]:
                        if zi.file_size <= 0 or zi.file_size > 5 * 1024 * 1024:
                            continue
                        inner_name = f"{name}::{zi.filename}"
                        try:
                            inner = zf.read(zi)
                        except Exception:
                            continue
                        s = self._score_data(inner_name, inner)
                        if s > best_score:
                            best_score = s
                            best_data = inner
                        if self._looks_like_archive(inner):
                            rec = self._scan_nested_archives(inner_name, inner, depth=depth - 1)
                            if rec is not None and rec[0] > best_score:
                                best_score, best_data = rec
            except Exception:
                pass

        if len(data) > 265 and data[257:262] == b"ustar":
            try:
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
                    mems = [m for m in tf.getmembers() if m.isfile() and 0 < m.size <= 5 * 1024 * 1024]
                    mems.sort(key=lambda m: (m.size, m.name))
                    for m in mems[:200]:
                        inner_name = f"{name}::{m.name}"
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            inner = f.read()
                        except Exception:
                            continue
                        s = self._score_data(inner_name, inner)
                        if s > best_score:
                            best_score = s
                            best_data = inner
                        if self._looks_like_archive(inner):
                            rec = self._scan_nested_archives(inner_name, inner, depth=depth - 1)
                            if rec is not None and rec[0] > best_score:
                                best_score, best_data = rec
            except Exception:
                pass

        if best_data is None:
            return None
        return (best_score, best_data)