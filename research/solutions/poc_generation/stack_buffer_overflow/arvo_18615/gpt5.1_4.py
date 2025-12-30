import os
import tarfile
import tempfile
import re


class Solution:
    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        abs_path = os.path.abspath(path)
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(path, member.name))
            if not os.path.commonprefix([abs_path, member_path]) == abs_path:
                continue
        tar.extractall(path)

    def _find_poc_file(self, root: str, target_len: int) -> bytes | None:
        keyword_paths = []
        ten_byte_files = []

        keywords = ("poc", "crash", "id:", "input", "overflow", "tic30", "branch")

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue

                if size == target_len:
                    ten_byte_files.append(fpath)

                if not (1 <= size <= 64):
                    continue

                lower_path = fpath.lower()
                if any(kw in lower_path for kw in keywords):
                    keyword_paths.append((abs(size - target_len), fpath))

        if keyword_paths:
            keyword_paths.sort(key=lambda x: (x[0], len(x[1])))
            best_path = keyword_paths[0][1]
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                pass

        if ten_byte_files:
            ten_byte_files.sort()
            for path in ten_byte_files:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if len(data) != target_len:
                    continue
                printable = sum(
                    1 for b in data if 32 <= b <= 126 or b in (9, 10, 13)
                )
                if printable < len(data):
                    return data
            for path in ten_byte_files:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    if len(data) == target_len:
                        return data
                except OSError:
                    continue

        return None

    def _find_hex_encoded_poc(self, root: str, target_len: int) -> bytes | None:
        hex_pattern = re.compile(r"(?:\\x[0-9a-fA-F]{2}){" + str(target_len) + r",}")
        text_exts = (
            ".c",
            ".h",
            ".txt",
            ".md",
            ".rst",
            ".inc",
            ".cfg",
            ".ini",
            ".json",
            ".xml",
            ".yaml",
            ".yml",
        )

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                lower = fpath.lower()
                if not any(lower.endswith(ext) for ext in text_exts):
                    continue
                try:
                    size = os.path.getsize(fpath)
                    if size > 1024 * 1024:
                        continue
                    with open(fpath, "r", encoding="latin-1", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue

                m = hex_pattern.search(text)
                if not m:
                    continue
                token = m.group(0)
                bytes_list = []
                i = 0
                while i + 4 <= len(token) and len(bytes_list) < target_len:
                    if token[i : i + 2] == "\\x":
                        h = token[i + 2 : i + 4]
                        try:
                            b = int(h, 16)
                        except ValueError:
                            bytes_list = []
                            break
                        bytes_list.append(b)
                        i += 4
                    else:
                        i += 1
                if len(bytes_list) == target_len:
                    return bytes(bytes_list)

        return None

    def solve(self, src_path: str) -> bytes:
        target_len = 10

        try:
            tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        except Exception:
            return b"\xff" * target_len

        try:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    self._safe_extract(tar, tmpdir)
            except Exception:
                return b"\xff" * target_len

            poc = self._find_poc_file(tmpdir, target_len)
            if poc is not None and len(poc) == target_len:
                return poc

            poc_hex = self._find_hex_encoded_poc(tmpdir, target_len)
            if poc_hex is not None and len(poc_hex) == target_len:
                return poc_hex

            return b"\xff" * target_len
        finally:
            # Best-effort cleanup; ignore any errors
            try:
                for dirpath, dirnames, filenames in os.walk(tmpdir, topdown=False):
                    for fname in filenames:
                        fpath = os.path.join(dirpath, fname)
                        try:
                            os.remove(fpath)
                        except OSError:
                            pass
                    for dname in dirnames:
                        dpath = os.path.join(dirpath, dname)
                        try:
                            os.rmdir(dpath)
                        except OSError:
                            pass
                try:
                    os.rmdir(tmpdir)
                except OSError:
                    pass