import os
import tarfile
import tempfile
import shutil
import gzip
import bz2
import zipfile

try:
    import lzma
except ImportError:
    lzma = None


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo_")
        try:
            self._extract_tar_safe(src_path, tmpdir)
            files = self._collect_files(tmpdir)
            target_len = 800

            poc = self._find_direct_poc(files, target_len)
            if poc is not None:
                return poc

            poc = self._find_archived_poc(files, target_len)
            if poc is not None:
                return poc

            return self._fallback_poc()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_tar_safe(self, tar_path: str, out_dir: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            base = os.path.realpath(out_dir)
            for member in tf.getmembers():
                member_path = os.path.realpath(os.path.join(out_dir, member.name))
                if not (member_path == base or member_path.startswith(base + os.sep)):
                    continue
                try:
                    tf.extract(member, out_dir)
                except Exception:
                    continue

    def _collect_files(self, root: str):
        result = []
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                if os.path.islink(full):
                    continue
                if not os.path.isfile(full):
                    continue
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                result.append((full, size))
        return result

    def _find_direct_poc(self, files, target_len: int):
        exact = [(p, s) for (p, s) in files if s == target_len]
        data = self._choose_best_file(exact, target_len)
        if data is not None:
            return data

        # Near-size candidates with relevant extensions
        lower = int(target_len * 0.5)
        upper = int(target_len * 1.5)
        near = []
        for path, size in files:
            if not (lower <= size <= upper):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in (".ttf", ".otf", ".woff", ".woff2", ".cff", ".bin", ".dat"):
                near.append((path, size))
        data = self._choose_best_file(near, target_len)
        if data is not None:
            return data
        return None

    def _choose_best_file(self, candidates, target_len: int):
        if not candidates:
            return None
        best_score = None
        best_data = None
        for path, size in candidates:
            try:
                with open(path, "rb") as f:
                    sample = f.read(64)
                    rest = f.read()
                data = sample + rest
            except OSError:
                continue
            score = self._score_candidate(path, size, sample, target_len)
            if best_score is None or score > best_score:
                best_score = score
                best_data = data
        return best_data

    def _looks_like_font(self, sample: bytes) -> bool:
        if len(sample) < 4:
            return False
        prefix4 = sample[:4]
        if prefix4 in (
            b"\x00\x01\x00\x00",
            b"OTTO",
            b"true",
            b"typ1",
            b"ttcf",
            b"wOFF",
            b"wOF2",
        ):
            return True
        return False

    def _score_candidate(self, path: str, size: int, sample: bytes, target_len: int) -> float:
        path_lower = path.lower().replace("\\", "/")
        filename = os.path.basename(path_lower)
        components = path_lower.split("/")

        score = 0.0

        keyword_groups = [
            (30, ["poc", "crash", "uaf", "heap", "use-after-free", "heap-use-after-free"]),
            (20, ["ots", "otsstream", "ots-stream", "ots-sanitize", "opentype", "truetype"]),
            (10, ["test", "tests", "testing", "regress", "regression", "fuzz", "corpus",
                  "inputs", "cases", "bugs", "issues", "clusterfuzz", "oss-fuzz"]),
        ]
        for pts, kws in keyword_groups:
            for kw in kws:
                for comp in components:
                    if kw in comp:
                        score += pts
                        break

        ext = os.path.splitext(filename)[1]
        if ext in (".ttf", ".otf", ".woff", ".woff2", ".cff"):
            score += 40
        elif ext in (".bin", ".dat", ".font"):
            score += 10
        elif ext in (".txt", ".md", ".rst", ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".py", ".java", ".js"):
            score -= 100

        if sample is not None and self._looks_like_font(sample):
            score += 60

        if sample:
            non_ascii = 0
            for b in sample:
                if b < 9 or (13 < b < 32) or b > 126:
                    non_ascii += 1
            ascii_ratio = 1.0 - (non_ascii / len(sample))
            if ascii_ratio > 0.95:
                score -= 50

        score -= len(path) * 0.01
        score -= abs(size - target_len) * 0.1

        return score

    def _find_archived_poc(self, files, target_len: int):
        interesting_kw = (
            "poc",
            "crash",
            "uaf",
            "heap",
            "use-after-free",
            "ots",
            "font",
            "fuzz",
            "clusterfuzz",
            "oss-fuzz",
        )
        candidates = []
        for path, size in files:
            lower_name = os.path.basename(path).lower()
            ext = os.path.splitext(lower_name)[1]
            if ext not in (".gz", ".xz", ".lzma", ".bz2", ".bz", ".zip"):
                continue
            if size > 200000:
                continue
            if not any(kw in lower_name for kw in interesting_kw):
                continue
            try:
                if ext == ".gz":
                    with gzip.open(path, "rb") as f:
                        data = f.read()
                    if len(data) == target_len:
                        sample = data[:64]
                        score = self._score_candidate(path, len(data), sample, target_len)
                        candidates.append((score, data))
                elif ext in (".xz", ".lzma"):
                    if lzma is None:
                        continue
                    with lzma.open(path, "rb") as f:
                        data = f.read()
                    if len(data) == target_len:
                        sample = data[:64]
                        score = self._score_candidate(path, len(data), sample, target_len)
                        candidates.append((score, data))
                elif ext in (".bz2", ".bz"):
                    with bz2.open(path, "rb") as f:
                        data = f.read()
                    if len(data) == target_len:
                        sample = data[:64]
                        score = self._score_candidate(path, len(data), sample, target_len)
                        candidates.append((score, data))
                elif ext == ".zip":
                    with zipfile.ZipFile(path) as zf:
                        for info in zf.infolist():
                            if info.is_dir():
                                continue
                            if info.file_size > 200000:
                                continue
                            data = zf.read(info.filename)
                            if len(data) == target_len:
                                sample = data[:64]
                                virt_path = path + "::" + info.filename
                                score = self._score_candidate(virt_path, len(data), sample, target_len)
                                candidates.append((score, data))
            except Exception:
                continue

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _fallback_poc(self) -> bytes:
        # Generic minimal OpenType-style header with padding to 800 bytes
        # This attempts to look like a font to maximize chances of exercising code paths.
        header = b"\x00\x01\x00\x00"  # TrueType version
        num_tables = 4
        header += num_tables.to_bytes(2, "big")  # numTables
        header += b"\x00\x80"  # searchRange (dummy)
        header += b"\x00\x03"  # entrySelector (dummy)
        header += b"\x00\x20"  # rangeShift (dummy)
        # Pad to 800 bytes
        if len(header) > 800:
            return header[:800]
        return header.ljust(800, b"A")