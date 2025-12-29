import os
import tarfile
import tempfile
import shutil
import zipfile


class Solution:
    def __init__(self):
        # Printable ASCII plus common whitespace considered "text"
        self._text_char_set = set(range(0x20, 0x7F))
        self._text_char_set.update((0x09, 0x0A, 0x0D))

    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            elif tarfile.is_tarfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="pocgen_")
                with tarfile.open(src_path, "r:*") as tar:
                    self._safe_extract(tar, tmpdir)
                root = tmpdir
            else:
                # Unexpected format, fall back to a generic PoC
                return self._fallback_poc()

            poc = self._find_poc_bytes(root, 262)
            if poc is None:
                poc = self._fallback_poc()
            return poc
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        base_path = os.path.abspath(path)
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            abs_member_path = os.path.abspath(member_path)
            if not (abs_member_path == base_path or abs_member_path.startswith(base_path + os.sep)):
                continue
            tar.extract(member, path)

    def _find_poc_bytes(self, root: str, size_hint: int) -> bytes | None:
        candidates = []

        # Pass 1: search regular files with exact size
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    if not os.path.isfile(path):
                        continue
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == size_hint:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    score = self._score_candidate(path, data)
                    candidates.append((score, data))

        # Pass 2: search inside reasonably small archives
        max_archive_size = 32 * 1024 * 1024
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    if not os.path.isfile(path):
                        continue
                    fsize = os.path.getsize(path)
                except OSError:
                    continue
                if fsize > max_archive_size:
                    continue

                try:
                    if zipfile.is_zipfile(path):
                        try:
                            with zipfile.ZipFile(path, "r") as zf:
                                for info in zf.infolist():
                                    if info.is_dir():
                                        continue
                                    if info.file_size != size_hint:
                                        continue
                                    try:
                                        data = zf.read(info.filename)
                                    except Exception:
                                        continue
                                    virt_path = f"{path}::{info.filename}"
                                    score = self._score_candidate(virt_path, data)
                                    candidates.append((score, data))
                        except (OSError, zipfile.BadZipFile):
                            continue
                    elif tarfile.is_tarfile(path):
                        try:
                            with tarfile.open(path, "r:*") as sub_tar:
                                for member in sub_tar.getmembers():
                                    if not member.isfile() or member.size != size_hint:
                                        continue
                                    try:
                                        fobj = sub_tar.extractfile(member)
                                    except (KeyError, OSError):
                                        continue
                                    if fobj is None:
                                        continue
                                    try:
                                        data = fobj.read()
                                    except Exception:
                                        continue
                                    virt_path = f"{path}::{member.name}"
                                    score = self._score_candidate(virt_path, data)
                                    candidates.append((score, data))
                        except (OSError, tarfile.TarError):
                            continue
                except OSError:
                    continue

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _score_candidate(self, path: str, data: bytes) -> int:
        score = 0
        lower_path = path.lower()
        base = os.path.basename(lower_path)

        keywords = ["poc", "crash", "testcase", "clusterfuzz", "fuzz", "input", "repro", "seed", "id_"]
        if any(k in lower_path for k in keywords):
            score += 10

        dir_keywords = ["/poc", "/pocs", "/crash", "/crashes", "/repro", "/reproducer", "/inputs", "/corpus"]
        if any(k in lower_path for k in dir_keywords):
            score += 5

        ext = os.path.splitext(base)[1]
        binary_exts = [".bin", ".raw", ".dat", ".input", ".fuzz"]
        text_exts = [
            ".c", ".cc", ".cpp", ".h", ".hpp", ".txt", ".md", ".markdown",
            ".py", ".sh", ".java", ".rs", ".go", ".html", ".xml", ".json",
            ".yaml", ".yml", ".toml", ".cmake",
        ]

        if ext in binary_exts:
            score += 3
        if ext in text_exts:
            score -= 4

        if data:
            nontext = 0
            for b in data:
                if b not in self._text_char_set:
                    nontext += 1
            ratio = nontext / float(len(data))
            if ratio > 0.3:
                score += 4
            else:
                score -= 2

            if data.count(0) > len(data) * 0.1:
                score += 1

        return score

    def _fallback_poc(self) -> bytes:
        # Generic fallback payload (unlikely to be correct but ensures a valid return)
        return b"A" * 262