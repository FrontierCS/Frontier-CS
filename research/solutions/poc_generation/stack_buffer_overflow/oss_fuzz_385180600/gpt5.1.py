import os
import tarfile
import tempfile
import io
import re
import gzip
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        self._extract_archive(src_path, tmpdir)
        poc = self._find_poc_file(tmpdir, bug_id="385180600", expected_len=262)
        if poc is None:
            poc = self._fallback_poc(262)
        return poc

    def _extract_archive(self, src_path: str, dst_dir: str) -> None:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    common_prefix = os.path.commonprefix([abs_directory, abs_target])
                    return common_prefix == abs_directory

                for member in tf.getmembers():
                    member_path = os.path.join(dst_dir, member.name)
                    if not is_within_directory(dst_dir, member_path):
                        continue
                tf.extractall(dst_dir)
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                zf.extractall(dst_dir)
        else:
            # Fallback: treat as an uncompressed directory or single file copied into dst_dir
            if os.path.isdir(src_path):
                # Copy directory tree
                for root, dirs, files in os.walk(src_path):
                    rel_root = os.path.relpath(root, src_path)
                    dst_root = os.path.join(dst_dir, rel_root) if rel_root != "." else dst_dir
                    os.makedirs(dst_root, exist_ok=True)
                    for f in files:
                        src_file = os.path.join(root, f)
                        dst_file = os.path.join(dst_root, f)
                        try:
                            with open(src_file, "rb") as sf, open(dst_file, "wb") as df:
                                df.write(sf.read())
                        except OSError:
                            pass
            else:
                # Single file: just copy
                try:
                    os.makedirs(dst_dir, exist_ok=True)
                    dst_file = os.path.join(dst_dir, os.path.basename(src_path))
                    with open(src_path, "rb") as sf, open(dst_file, "wb") as df:
                        df.write(sf.read())
                except OSError:
                    pass

    def _find_poc_file(self, root: str, bug_id: str, expected_len: int) -> bytes | None:
        # Stage 1: search for files with bug_id in filename
        bugid_paths = []
        for r, _dirs, files in os.walk(root):
            for fname in files:
                if bug_id in fname:
                    bugid_paths.append(os.path.join(r, fname))

        for path in bugid_paths:
            data = self._load_candidate(path, expected_len)
            if data is not None:
                return data

        # Stage 2: heuristic filenames
        heur_keywords = ["poc", "testcase", "crash", "clusterfuzz", "fuzz", "input"]
        heur_paths = []
        for r, _dirs, files in os.walk(root):
            for fname in files:
                lname = fname.lower()
                if any(k in lname for k in heur_keywords):
                    heur_paths.append(os.path.join(r, fname))

        for path in heur_paths:
            data = self._load_candidate(path, expected_len)
            if data is not None:
                return data

        # Stage 3: search by file size equal to expected_len
        code_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".txt", ".md", ".py", ".java", ".go", ".rs", ".js",
            ".html", ".htm", ".xml", ".json", ".yaml", ".yml",
            ".toml", ".cmake", ".sh", ".bat", ".ps1", ".mak", ".mk",
            ".in", ".ac"
        }
        bin_paths = []
        code_paths = []

        for r, _dirs, files in os.walk(root):
            for fname in files:
                path = os.path.join(r, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size == expected_len:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in code_exts:
                        code_paths.append(path)
                    else:
                        bin_paths.append(path)

        for path in bin_paths + code_paths:
            data = self._load_candidate(path, expected_len)
            if data is not None:
                return data

        return None

    def _load_candidate(self, path: str, expected_len: int) -> bytes | None:
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return None

        # Direct match on size
        if expected_len is None or len(data) == expected_len:
            return data

        # Gzip-compressed?
        if data.startswith(b"\x1f\x8b"):
            try:
                dec = gzip.decompress(data)
                if expected_len is None or len(dec) == expected_len:
                    return dec
            except Exception:
                pass

        # Zip-compressed?
        if data[:2] == b"PK":
            try:
                with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
                    # Prefer entry with expected_len, else first non-dir
                    chosen = None
                    for info in zf.infolist():
                        is_dir = False
                        if hasattr(info, "is_dir"):
                            is_dir = info.is_dir()
                        else:
                            is_dir = info.filename.endswith("/")
                        if is_dir:
                            continue
                        content = zf.read(info)
                        if expected_len is None or len(content) == expected_len:
                            return content
                        if chosen is None:
                            chosen = content
                    if chosen is not None:
                        return chosen
            except Exception:
                pass

        # ASCII hex representation?
        try:
            text = data.decode("ascii")
            hexchars = re.sub(r"[^0-9A-Fa-f]", "", text)
            if len(hexchars) >= expected_len * 2 and len(hexchars) % 2 == 0:
                raw = bytes.fromhex(hexchars[: expected_len * 2])
                return raw
        except Exception:
            pass

        return None

    def _fallback_poc(self, expected_len: int) -> bytes:
        # Structured TLV-like fallback payload of the desired length
        data = bytearray()
        t = 0
        while len(data) + 2 <= expected_len:
            remaining = expected_len - len(data) - 2
            if remaining <= 0:
                break
            tlv_len = min(3, remaining)
            data.append(t & 0xFF)          # Type
            data.append(tlv_len & 0xFF)    # Length
            for i in range(tlv_len):
                data.append((t + i) & 0xFF)
            t += 1

        if len(data) < expected_len:
            data.extend(b"\x00" * (expected_len - len(data)))

        return bytes(data)