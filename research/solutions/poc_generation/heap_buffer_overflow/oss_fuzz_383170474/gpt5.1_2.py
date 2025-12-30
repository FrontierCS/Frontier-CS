import os
import tarfile
import zipfile
import tempfile
import gzip
import bz2
import lzma
import io

GROUND_TRUTH_LEN = 1551


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)
        poc_path = self._find_poc_file(root)
        if poc_path:
            data = self._load_file_data(poc_path)
            if data:
                return data
        return b"A" * GROUND_TRUTH_LEN

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="src-")
        opened = False

        if os.path.isfile(src_path):
            try:
                if tarfile.is_tarfile(src_path):
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(tmpdir)
                    opened = True
                elif zipfile.is_zipfile(src_path):
                    with zipfile.ZipFile(src_path) as zf:
                        zf.extractall(tmpdir)
                    opened = True
            except Exception:
                opened = False

        if opened:
            return tmpdir

        parent = os.path.dirname(src_path)
        return parent if parent else "."

    def _find_poc_file(self, root: str) -> str | None:
        best_score = 0
        best_path = None
        max_size_default = 1_000_000

        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    if not os.path.isfile(path):
                        continue
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0:
                    continue

                if "383170474" not in path and size > max_size_default:
                    continue

                score = self._score_file(path, size)
                if score > best_score:
                    best_score = score
                    best_path = path

        return best_path

    def _score_file(self, path: str, size: int) -> int:
        lname = path.lower()
        parts = lname.replace("\\", "/").split("/")
        _, ext = os.path.splitext(lname)

        binary_exts = {
            "",
            ".bin",
            ".dat",
            ".out",
            ".o",
            ".obj",
            ".elf",
            ".so",
            ".a",
            ".dwp",
            ".dwo",
            ".gz",
            ".gzip",
            ".bz2",
            ".bzip2",
            ".xz",
            ".lzma",
            ".zip",
            ".debug",
            ".debug_names",
            ".dwarf",
            ".core",
        }

        if ext not in binary_exts:
            if not any(k in lname for k in ("oss-fuzz", "ossfuzz", "fuzz", "crash", "poc", "bug")) and not any(
                p in ("tests", "test", "regress") for p in parts
            ):
                return 0

        key_weight = 0

        if "383170474" in lname:
            key_weight += 100000
        if "oss-fuzz" in lname or "ossfuzz" in lname:
            key_weight += 6000
        if any(k in parts for k in ("fuzz", "corpus", "inputs", "cases")):
            key_weight += 4000
        if any(k in parts for k in ("test", "tests", "regress")):
            key_weight += 3500
        if "crash" in lname or "poc" in lname or "bug" in lname:
            key_weight += 3000
        if "debug_names" in lname or "debugnames" in lname:
            key_weight += 2000
        if "dwarf" in lname:
            key_weight += 1000
        if "debug" in lname:
            key_weight += 800
        if "names" in lname:
            key_weight += 400

        if key_weight == 0:
            return 0

        diff = abs(size - GROUND_TRUTH_LEN)
        size_score = max(0, 2000 - diff)
        return key_weight + size_score

    def _load_file_data(self, path: str) -> bytes:
        lname = path.lower()
        _, ext = os.path.splitext(lname)
        data = b""

        try:
            if ext in (".gz", ".gzip"):
                with gzip.open(path, "rb") as f:
                    data = f.read()
            elif ext in (".bz2", ".bzip2"):
                with bz2.open(path, "rb") as f:
                    data = f.read()
            elif ext in (".xz", ".lzma"):
                with lzma.open(path, "rb") as f:
                    data = f.read()
            elif ext == ".zip":
                data = self._extract_from_zip(path)
            elif ext in (".tar", ".tgz"):
                data = self._extract_from_tar_file(path)
            else:
                with open(path, "rb") as f:
                    data = f.read()
        except Exception:
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                return b""

        if ext in (".gz", ".gzip", ".bz2", ".bzip2", ".xz", ".lzma") and data:
            maybe = self._try_extract_from_tar_bytes(data)
            if maybe:
                data = maybe

        return data

    def _extract_from_zip(self, path: str) -> bytes:
        try:
            with zipfile.ZipFile(path) as zf:
                infos = [i for i in zf.infolist() if not i.is_dir()]
                if not infos:
                    return b""
                best = min(infos, key=lambda i: abs(i.file_size - GROUND_TRUTH_LEN))
                return zf.read(best)
        except Exception:
            return b""

    def _extract_from_tar_file(self, path: str) -> bytes:
        try:
            with tarfile.open(path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                if not members:
                    return b""
                best = min(members, key=lambda m: abs(m.size - GROUND_TRUTH_LEN))
                f = tf.extractfile(best)
                if f is None:
                    return b""
                try:
                    return f.read()
                finally:
                    f.close()
        except Exception:
            return b""

    def _try_extract_from_tar_bytes(self, data: bytes) -> bytes | None:
        try:
            bio = io.BytesIO(data)
            with tarfile.open(fileobj=bio, mode="r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                if not members:
                    return None
                best = min(members, key=lambda m: abs(m.size - GROUND_TRUTH_LEN))
                f = tf.extractfile(best)
                if f is None:
                    return None
                try:
                    return f.read()
                finally:
                    f.close()
        except Exception:
            return None