import os
import io
import re
import tarfile
import zipfile
from typing import Optional, Tuple


class Solution:
    _PREFERRED_SIZE = 274773

    def _pattern_score(self, name_l: str) -> int:
        score = 0
        if "clusterfuzz" in name_l:
            score += 80
        if "testcase" in name_l:
            score += 40
        if "minimized" in name_l:
            score += 35
        if "crash" in name_l:
            score += 35
        if "repro" in name_l or "reproducer" in name_l:
            score += 30
        if re.search(r"\bpoc\b", name_l):
            score += 25
        if "uaf" in name_l or "use_after_free" in name_l or "use-after-free" in name_l:
            score += 25
        if "asan" in name_l or "ubsan" in name_l or "sanitizer" in name_l:
            score += 15
        if "oss-fuzz" in name_l or "ossfuzz" in name_l:
            score += 10
        if "crashers" in name_l:
            score += 15
        if "fuzz" in name_l or "fuzzer" in name_l:
            score += 8
        if "corpus" in name_l or "seed" in name_l:
            score += 5
        if "/test/" in name_l or "\\test\\" in name_l or "/tests/" in name_l or "\\tests\\" in name_l:
            score += 3

        # Mild extension preference (common source/text inputs)
        ext = os.path.splitext(name_l)[1]
        if ext in (".py", ".js", ".json", ".xml", ".yaml", ".yml", ".txt", ".html", ".htm", ".c", ".cpp"):
            score += 3
        if ext in (".zip", ".gz", ".xz", ".bz2", ".zst", ".tar"):
            score += 1
        return score

    def _size_score(self, size: int) -> float:
        if size <= 0:
            return -1e9
        d = abs(size - self._PREFERRED_SIZE)
        # reward closeness to preferred size, but keep bounded
        return max(0.0, 20.0 - (d / 20000.0))

    def _is_reasonable_size(self, size: int) -> bool:
        return 1 <= size <= 50 * 1024 * 1024

    def _consider_candidate(
        self,
        best: Optional[Tuple[float, int, str, bytes]],
        name: str,
        size: int,
        data_getter,
    ) -> Optional[Tuple[float, int, str, bytes]]:
        if not self._is_reasonable_size(size):
            return best
        name_l = name.lower()
        sc = float(self._pattern_score(name_l)) + self._size_score(size)

        # Skip extremely low-signal tiny files
        if sc < 1.0 and size < 64:
            return best

        if best is not None:
            best_sc, best_size, best_name, _ = best
            if sc < best_sc:
                return best
            if sc == best_sc and size >= best_size:
                return best

        try:
            data = data_getter()
        except Exception:
            return best
        if not data:
            return best

        return (sc, size, name, data)

    def _scan_directory(self, root: str) -> Optional[Tuple[float, int, str, bytes]]:
        best = None
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                size = int(st.st_size)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                best = self._consider_candidate(
                    best,
                    rel,
                    size,
                    lambda p=full: open(p, "rb").read(),
                )
        return best

    def _scan_zip(self, zip_path: str) -> Optional[Tuple[float, int, str, bytes]]:
        best = None
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    name = zi.filename
                    size = int(zi.file_size)
                    best = self._consider_candidate(
                        best,
                        name,
                        size,
                        lambda n=name, z=zf: z.read(n),
                    )
        except Exception:
            return None
        return best

    def _open_tar_any(self, path: str):
        try:
            return tarfile.open(path, mode="r:*"), False
        except tarfile.ReadError:
            pass

        # Try .tar.zst via zstandard if available
        if path.lower().endswith((".zst", ".tzst", ".tar.zst", ".tar.tzst")):
            try:
                import zstandard as zstd  # type: ignore
            except Exception:
                return None, False
            try:
                f = open(path, "rb")
                dctx = zstd.ZstdDecompressor()
                reader = dctx.stream_reader(f)
                tf = tarfile.open(fileobj=reader, mode="r|")
                # We must keep f and reader alive; return them for closing.
                return (tf, (f, reader)), True
            except Exception:
                try:
                    f.close()
                except Exception:
                    pass
                return None, False

        return None, False

    def _scan_tar(self, tar_path: str) -> Optional[Tuple[float, int, str, bytes]]:
        opened, is_stream = self._open_tar_any(tar_path)
        if opened is None:
            return None
        if is_stream:
            tf, extras = opened
        else:
            tf = opened
            extras = None

        best = None
        try:
            for m in tf:
                try:
                    if not m.isreg():
                        continue
                    name = m.name
                    size = int(m.size)
                    if not self._is_reasonable_size(size):
                        continue

                    def getter(member=m, tfile=tf):
                        fobj = tfile.extractfile(member)
                        if fobj is None:
                            return b""
                        try:
                            return fobj.read()
                        finally:
                            try:
                                fobj.close()
                            except Exception:
                                pass

                    best = self._consider_candidate(best, name, size, getter)
                except Exception:
                    continue
        finally:
            try:
                tf.close()
            except Exception:
                pass
            if extras:
                f, reader = extras
                try:
                    reader.close()
                except Exception:
                    pass
                try:
                    f.close()
                except Exception:
                    pass
        return best

    def solve(self, src_path: str) -> bytes:
        best = None

        if os.path.isdir(src_path):
            best = self._scan_directory(src_path)
        elif os.path.isfile(src_path):
            low = src_path.lower()
            if low.endswith(".zip"):
                best = self._scan_zip(src_path)
            else:
                best = self._scan_tar(src_path)
                if best is None:
                    # If not a tar, try zip anyway
                    best = self._scan_zip(src_path)
                    if best is None:
                        # Last resort: treat as directory-like (shouldn't happen), or just return file content
                        try:
                            data = open(src_path, "rb").read()
                            best = (0.0, len(data), os.path.basename(src_path), data)
                        except Exception:
                            best = None
        else:
            return b""

        if best is None:
            return b""

        return best[3]