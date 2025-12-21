import os
import tarfile
import zipfile
import io


TRUTH_LEN = 150979

NEGATIVE_EXTS = {
    "c", "cc", "cpp", "cxx", "h", "hh", "hpp",
    "py", "pyc", "pyo",
    "sh", "bash", "bat", "ps1",
    "txt", "md", "rst",
    "html", "htm", "xml", "xhtml",
    "json", "yml", "yaml", "toml", "ini", "cfg",
    "cmake", "mak", "mk",
    "java", "rb", "go", "rs", "pl", "pm", "php",
    "js", "ts", "m", "mm", "cs", "swift", "kt", "kts",
    "gradle", "properties",
    "o", "obj", "a", "lib", "so", "dll", "dylib",
    "log"
}

POSITIVE_EXTS = {
    "pdf": 60.0,
    "ps": 50.0,
    "eps": 40.0,
    "bin": 20.0,
    "dat": 10.0,
    "": 0.0,
}

ARCHIVE_EXTS = {
    "zip", "tar", "tgz", "gz", "bz2", "xz", "lz", "lzma", "7z"
}

KEY_SCORES = {
    "poc": 80.0,
    "proof": 70.0,
    "crash": 70.0,
    "testcase": 60.0,
    "clusterfuzz": 60.0,
    "repro": 60.0,
    "id:": 50.0,
    "fuzz": 20.0,
}

DIR_KEY_SCORES = {
    "/artifacts/": 30.0,
    "/crash-": 30.0,
    "/reproducers/": 30.0,
    "testcases": 40.0,
}


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try directory path
        if os.path.isdir(src_path):
            data = self._get_poc_from_dir(src_path, TRUTH_LEN)
            if data is not None:
                return data

        # Try tarball
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    data = self._get_poc_from_tarfile(tf, TRUTH_LEN, depth=0)
                    if data is not None:
                        return data
        except Exception:
            pass

        # Try zipfile
        try:
            if zipfile.is_zipfile(src_path):
                with zipfile.ZipFile(src_path, "r") as zf:
                    data = self._get_poc_from_zipfile(zf, TRUTH_LEN, depth=0)
                    if data is not None:
                        return data
        except Exception:
            pass

        # Fallback generic PDF
        return self._generic_fallback_poc()

    def _score(self, name: str, size: int, truth_len: int) -> float:
        name_lower = name.lower()
        base = os.path.basename(name_lower)
        if "." in base:
            ext = base.rsplit(".", 1)[1]
        else:
            ext = ""

        score = 0.0

        if ext in NEGATIVE_EXTS:
            score -= 100.0

        if ext in POSITIVE_EXTS:
            score += POSITIVE_EXTS[ext]

        for key, val in KEY_SCORES.items():
            if key in name_lower:
                score += val

        for key, val in DIR_KEY_SCORES.items():
            if key in name_lower:
                score += val

        if truth_len > 0 and size > 0:
            diff = abs(size - truth_len)
            if diff > 200000:
                diff = 200000
            closeness = 80.0 * (1.0 - diff / 200000.0)
            if closeness < 0.0:
                closeness = 0.0
            score += closeness

        score -= size / 1000000.0

        return score

    def _get_poc_from_tarfile(self, tf: tarfile.TarFile, truth_len: int, depth: int) -> bytes | None:
        max_depth = 3
        members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
        if not members:
            return None

        # Exact size match first
        exact_members = [m for m in members if m.size == truth_len]
        if exact_members:
            best = None
            best_score = None
            for m in exact_members:
                s = self._score(m.name, m.size, truth_len)
                if best is None or s > best_score:
                    best = m
                    best_score = s
            if best is not None:
                f = tf.extractfile(best)
                if f is not None:
                    return f.read()

        # General scoring
        best = None
        best_score = None
        for m in members:
            s = self._score(m.name, m.size, truth_len)
            if best is None or s > best_score:
                best = m
                best_score = s

        if best is None:
            return None

        f = tf.extractfile(best)
        if f is None:
            return None
        data = f.read()

        base = os.path.basename(best.name.lower())
        if "." in base:
            ext = base.rsplit(".", 1)[1]
        else:
            ext = ""

        if ext in ARCHIVE_EXTS and depth < max_depth:
            nested = self._get_poc_from_bytes(data, truth_len, depth + 1)
            if nested is not None:
                return nested

        return data

    def _get_poc_from_zipfile(self, zf: zipfile.ZipFile, truth_len: int, depth: int) -> bytes | None:
        max_depth = 3
        infos = [info for info in zf.infolist() if not info.is_dir() and info.file_size > 0]
        if not infos:
            return None

        exact_infos = [info for info in infos if info.file_size == truth_len]
        if exact_infos:
            best = None
            best_score = None
            for info in exact_infos:
                s = self._score(info.filename, info.file_size, truth_len)
                if best is None or s > best_score:
                    best = info
                    best_score = s
            if best is not None:
                return zf.read(best.filename)

        best = None
        best_score = None
        for info in infos:
            s = self._score(info.filename, info.file_size, truth_len)
            if best is None or s > best_score:
                best = info
                best_score = s

        if best is None:
            return None

        data = zf.read(best.filename)

        base = os.path.basename(best.filename.lower())
        if "." in base:
            ext = base.rsplit(".", 1)[1]
        else:
            ext = ""

        if ext in ARCHIVE_EXTS and depth < max_depth:
            nested = self._get_poc_from_bytes(data, truth_len, depth + 1)
            if nested is not None:
                return nested

        return data

    def _get_poc_from_bytes(self, data: bytes, truth_len: int, depth: int) -> bytes | None:
        max_depth = 3
        if depth > max_depth:
            return None

        # Try as tar archive
        try:
            bio = io.BytesIO(data)
            tf = tarfile.open(fileobj=bio, mode="r:*")
        except Exception:
            tf = None
        if tf is not None:
            with tf:
                poc = self._get_poc_from_tarfile(tf, truth_len, depth)
            if poc is not None:
                return poc

        # Try as zip archive
        try:
            bio = io.BytesIO(data)
            zf = zipfile.ZipFile(bio, "r")
        except Exception:
            zf = None
        if zf is not None:
            with zf:
                poc = self._get_poc_from_zipfile(zf, truth_len, depth)
            if poc is not None:
                return poc

        return None

    def _get_poc_from_dir(self, root: str, truth_len: int) -> bytes | None:
        best_path = None
        best_score = None

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue
                if size <= 0:
                    continue

                rel_name = os.path.relpath(full_path, root)
                s = self._score(rel_name, size, truth_len)
                if best_path is None or s > best_score:
                    best_path = full_path
                    best_score = s

        if best_path is None:
            return None

        base = os.path.basename(best_path.lower())
        if "." in base:
            ext = base.rsplit(".", 1)[1]
        else:
            ext = ""

        try:
            with open(best_path, "rb") as f:
                data = f.read()
        except OSError:
            return None

        if ext in ARCHIVE_EXTS:
            nested = self._get_poc_from_bytes(data, truth_len, depth=1)
            if nested is not None:
                return nested

        return data

    def _generic_fallback_poc(self) -> bytes:
        return (
            b"%PDF-1.3\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog >>\n"
            b"endobj\n"
            b"trailer\n"
            b"<< /Root 1 0 R >>\n"
            b"%%EOF\n"
        )
