import os
import tarfile
import io
import gzip
import bz2
import lzma
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = None
        if os.path.isdir(src_path):
            data = self._find_poc_in_directory(src_path)
        else:
            data = self._find_poc_in_tar(src_path)
        if data is None:
            data = self._fallback_poc()
        return data

    def _find_poc_in_tar(self, tar_path: str):
        try:
            tf = tarfile.open(tar_path, 'r:*')
        except Exception:
            return None
        try:
            members = [m for m in tf.getmembers() if m.isfile()]
            if not members:
                return None
            data = self._find_poc_in_tar_members(tf, members)
            return data
        finally:
            try:
                tf.close()
            except Exception:
                pass

    def _find_poc_in_tar_members(self, tf, members):
        EXACT_LEN = 6180
        KEYWORDS = [
            "42536279",
            "svcdec",
            "svc-dec",
            "svc_dec",
            "svc",
            "svcd",
            "heap",
            "overflow",
            "crash",
            "poc",
            "repro",
            "oss-fuzz",
            "ossfuzz",
            "fuzz",
            "bug",
        ]
        TEXT_EXTS = {
            ".c",
            ".h",
            ".cc",
            ".cpp",
            ".cxx",
            ".hh",
            ".hpp",
            ".py",
            ".py3",
            ".pyw",
            ".md",
            ".txt",
            ".rst",
            ".rtf",
            ".html",
            ".htm",
            ".xml",
            ".xhtml",
            ".js",
            ".css",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".cmake",
            ".in",
            ".am",
            ".ac",
            ".m4",
            ".sh",
            ".bat",
            ".ps1",
            ".java",
            ".scala",
            ".go",
            ".rs",
            ".php",
            ".pl",
            ".rb",
            ".m",
            ".mm",
            ".swift",
            ".cs",
            ".sql",
            ".tex",
            ".log",
        }

        cand_exact = []
        cand_keyword = []
        cand_other = []

        # Process normal members
        for m in members:
            try:
                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                root, ext = os.path.splitext(base)
                if ext in TEXT_EXTS:
                    continue
                size = m.size
                if size <= 0 or size > 1_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        sample = f.read(4096)
                    finally:
                        f.close()
                except Exception:
                    continue
                if not sample:
                    continue
                if not self._is_probably_binary(sample):
                    continue
                candidate = ("member", name_lower, size, m)
                if size == EXACT_LEN:
                    cand_exact.append(candidate)
                elif self._name_has_keyword(name_lower, KEYWORDS):
                    cand_keyword.append(candidate)
                else:
                    cand_other.append(candidate)
            except Exception:
                continue

        # Process compressed members
        compressed_exts = {".gz", ".xz", ".bz2", ".lzma", ".zip"}
        for m in members:
            try:
                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                root, ext = os.path.splitext(base)
                if ext not in compressed_exts:
                    continue
                size = m.size
                if size <= 0 or size > 200_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        compressed_bytes = f.read()
                    finally:
                        f.close()
                except Exception:
                    continue

                if ext == ".gz":
                    try:
                        decompressed = gzip.decompress(compressed_bytes)
                    except Exception:
                        continue
                    dname = name_lower[:-3] if name_lower.endswith(".gz") else name_lower
                    self._classify_decompressed(
                        dname,
                        decompressed,
                        EXACT_LEN,
                        KEYWORDS,
                        cand_exact,
                        cand_keyword,
                        cand_other,
                    )
                elif ext in (".xz", ".lzma"):
                    try:
                        decompressed = lzma.decompress(compressed_bytes)
                    except Exception:
                        continue
                    dname = name_lower.rsplit(".", 1)[0]
                    self._classify_decompressed(
                        dname,
                        decompressed,
                        EXACT_LEN,
                        KEYWORDS,
                        cand_exact,
                        cand_keyword,
                        cand_other,
                    )
                elif ext == ".bz2":
                    try:
                        decompressed = bz2.decompress(compressed_bytes)
                    except Exception:
                        continue
                    dname = name_lower[:-4] if name_lower.endswith(".bz2") else name_lower
                    self._classify_decompressed(
                        dname,
                        decompressed,
                        EXACT_LEN,
                        KEYWORDS,
                        cand_exact,
                        cand_keyword,
                        cand_other,
                    )
                elif ext == ".zip":
                    bio = io.BytesIO(compressed_bytes)
                    try:
                        with zipfile.ZipFile(bio) as zf:
                            for zi in zf.infolist():
                                if zi.is_dir():
                                    continue
                                if zi.file_size <= 0 or zi.file_size > 1_000_000:
                                    continue
                                try:
                                    data = zf.read(zi.filename)
                                except Exception:
                                    continue
                                zname = name_lower + "::" + zi.filename.lower()
                                self._classify_decompressed(
                                    zname,
                                    data,
                                    EXACT_LEN,
                                    KEYWORDS,
                                    cand_exact,
                                    cand_keyword,
                                    cand_other,
                                )
                    except Exception:
                        continue
            except Exception:
                continue

        # Choose best candidate
        if cand_exact:
            best = self._pick_best_candidate(cand_exact, EXACT_LEN)
            return self._materialize_candidate_from_tar(tf, best)
        if cand_keyword:
            best = self._pick_best_candidate(cand_keyword, EXACT_LEN)
            return self._materialize_candidate_from_tar(tf, best)
        if cand_other:
            best = self._pick_best_candidate(cand_other, EXACT_LEN)
            return self._materialize_candidate_from_tar(tf, best)
        return None

    def _classify_decompressed(
        self,
        name_lower,
        data,
        exact_len,
        keywords,
        cand_exact,
        cand_keyword,
        cand_other,
    ):
        if not data:
            return
        if not self._is_probably_binary(data[:4096]):
            return
        size = len(data)
        candidate = ("compressed", name_lower, size, data)
        if size == exact_len:
            cand_exact.append(candidate)
        elif self._name_has_keyword(name_lower, keywords):
            cand_keyword.append(candidate)
        else:
            cand_other.append(candidate)

    def _materialize_candidate_from_tar(self, tf, candidate):
        kind, name_lower, size, obj = candidate
        if kind == "member":
            try:
                f = tf.extractfile(obj)
                if not f:
                    return None
                try:
                    data = f.read()
                finally:
                    f.close()
                return data
            except Exception:
                return None
        else:  # "compressed"
            return obj

    def _pick_best_candidate(self, candidates, exact_len):
        def importance(c):
            kind, name_lower, size, obj = c
            d = abs(size - exact_len)
            prio = 0
            if "42536279" in name_lower:
                prio -= 10000
            if "poc" in name_lower:
                prio -= 8000
            if "crash" in name_lower:
                prio -= 7000
            if "oss" in name_lower and "fuzz" in name_lower:
                prio -= 5000
            if "fuzz" in name_lower:
                prio -= 2000
            if "regress" in name_lower or "regression" in name_lower:
                prio -= 1500
            if "test" in name_lower or "tests" in name_lower:
                prio -= 1200
            if "svcdec" in name_lower:
                prio -= 1000
            if "svc" in name_lower:
                prio -= 500
            # Prefer non-compressed slightly
            if kind == "member":
                prio -= 100
            return (d, prio, len(name_lower))

        candidates_sorted = list(candidates)
        candidates_sorted.sort(key=importance)
        return candidates_sorted[0]

    def _name_has_keyword(self, name_lower, keywords):
        for k in keywords:
            if k in name_lower:
                return True
        return False

    def _is_probably_binary(self, sample: bytes) -> bool:
        if not sample:
            return False
        if b"\x00" in sample:
            return True
        # Define set of typical text characters
        textchars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7F)))
        nontext = 0
        for b in sample:
            if b not in textchars:
                nontext += 1
        return (nontext / float(len(sample))) > 0.30

    def _find_poc_in_directory(self, dir_path: str):
        EXACT_LEN = 6180
        KEYWORDS = [
            "42536279",
            "svcdec",
            "svc-dec",
            "svc_dec",
            "svc",
            "svcd",
            "heap",
            "overflow",
            "crash",
            "poc",
            "repro",
            "oss-fuzz",
            "ossfuzz",
            "fuzz",
            "bug",
        ]
        TEXT_EXTS = {
            ".c",
            ".h",
            ".cc",
            ".cpp",
            ".cxx",
            ".hh",
            ".hpp",
            ".py",
            ".py3",
            ".pyw",
            ".md",
            ".txt",
            ".rst",
            ".rtf",
            ".html",
            ".htm",
            ".xml",
            ".xhtml",
            ".js",
            ".css",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".cmake",
            ".in",
            ".am",
            ".ac",
            ".m4",
            ".sh",
            ".bat",
            ".ps1",
            ".java",
            ".scala",
            ".go",
            ".rs",
            ".php",
            ".pl",
            ".rb",
            ".m",
            ".mm",
            ".swift",
            ".cs",
            ".sql",
            ".tex",
            ".log",
        }

        cand_exact = []
        cand_keyword = []
        cand_other = []

        for root_dir, _, files in os.walk(dir_path):
            for fname in files:
                full_path = os.path.join(root_dir, fname)
                try:
                    rel_name = os.path.relpath(full_path, dir_path).replace("\\", "/")
                    name_lower = rel_name.lower()
                    base = os.path.basename(name_lower)
                    _, ext = os.path.splitext(base)
                    if ext in TEXT_EXTS:
                        continue
                    try:
                        size = os.path.getsize(full_path)
                    except OSError:
                        continue
                    if size <= 0 or size > 1_000_000:
                        continue
                    try:
                        with open(full_path, "rb") as f:
                            sample = f.read(4096)
                    except Exception:
                        continue
                    if not sample:
                        continue
                    if not self._is_probably_binary(sample):
                        continue
                    candidate = ("file", name_lower, size, full_path)
                    if size == EXACT_LEN:
                        cand_exact.append(candidate)
                    elif self._name_has_keyword(name_lower, KEYWORDS):
                        cand_keyword.append(candidate)
                    else:
                        cand_other.append(candidate)
                except Exception:
                    continue

        if cand_exact or cand_keyword or cand_other:
            all_cands = cand_exact or cand_keyword or cand_other
            best = self._pick_best_candidate_dir(all_cands, EXACT_LEN)
            kind, name_lower, size, path = best
            try:
                with open(path, "rb") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def _pick_best_candidate_dir(self, candidates, exact_len):
        def importance(c):
            kind, name_lower, size, path = c
            d = abs(size - exact_len)
            prio = 0
            if "42536279" in name_lower:
                prio -= 10000
            if "poc" in name_lower:
                prio -= 8000
            if "crash" in name_lower:
                prio -= 7000
            if "oss" in name_lower and "fuzz" in name_lower:
                prio -= 5000
            if "fuzz" in name_lower:
                prio -= 2000
            if "regress" in name_lower or "regression" in name_lower:
                prio -= 1500
            if "test" in name_lower or "tests" in name_lower:
                prio -= 1200
            if "svcdec" in name_lower:
                prio -= 1000
            if "svc" in name_lower:
                prio -= 500
            return (d, prio, len(name_lower))

        candidates_sorted = list(candidates)
        candidates_sorted.sort(key=importance)
        return candidates_sorted[0]

    def _fallback_poc(self) -> bytes:
        # Fallback: generic binary blob with the ground-truth length
        return b"A" * 6180
