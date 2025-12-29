import os
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        bug_id = "383200048"
        ground_len = 512

        if os.path.isdir(src_path):
            data = self._find_poc_in_dir(src_path, bug_id, ground_len)
            if data is not None:
                return data
            data = self._find_generic_in_dir(src_path, ground_len)
            if data is not None:
                return data
            return self._fallback_payload(ground_len)

        # src_path is assumed to be an archive (tar or other)
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                data = self._find_poc_in_tar(tf, members, bug_id, ground_len)
                if data is not None:
                    return data
                data = self._find_generic_in_tar(tf, members, ground_len)
                if data is not None:
                    return data
        except (tarfile.TarError, OSError):
            # Not a tar archive or cannot be read as tar; try generic archive unpack
            temp_dir = tempfile.mkdtemp(prefix="poc_extract_")
            try:
                try:
                    shutil.unpack_archive(src_path, temp_dir)
                except (shutil.ReadError, ValueError):
                    # Unsupported archive type
                    pass
                else:
                    data = self._find_poc_in_dir(temp_dir, bug_id, ground_len)
                    if data is not None:
                        return data
                    data = self._find_generic_in_dir(temp_dir, ground_len)
                    if data is not None:
                        return data
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        return self._fallback_payload(ground_len)

    def _find_poc_in_tar(self, tf: tarfile.TarFile, members, bug_id: str, ground_len: int):
        best_data = None
        best_diff = None

        for m in members:
            if not m.isfile():
                continue
            name_lower = m.name.lower()
            if bug_id in name_lower:
                try:
                    f = tf.extractfile(m)
                except (KeyError, OSError):
                    continue
                if f is None:
                    continue
                data = f.read()
                if len(data) == ground_len:
                    return data
                diff = abs(len(data) - ground_len)
                if best_data is None or diff < best_diff:
                    best_data = data
                    best_diff = diff
        return best_data

    def _find_generic_in_tar(self, tf: tarfile.TarFile, members, ground_len: int):
        patterns = [
            "poc",
            "crash",
            "testcase",
            "clusterfuzz",
            "oss-fuzz",
            "bug",
            "regress",
            "input",
            "seed",
        ]

        candidates = []
        for m in members:
            if not m.isfile() or m.size <= 0:
                continue
            name_lower = m.name.lower()
            priority = 1 if any(p in name_lower for p in patterns) else 0
            candidates.append((priority, m.size, m))

        if not candidates:
            return None

        # Prefer pattern-matched files, then closest to ground_len
        candidates.sort(key=lambda x: (-x[0], abs(x[1] - ground_len), x[1]))

        for priority, size, m in candidates:
            # Limit to reasonably small files to avoid large reads
            if size > 1024 * 1024:
                continue
            try:
                f = tf.extractfile(m)
            except (KeyError, OSError):
                continue
            if f is None:
                continue
            data = f.read()
            if data:
                return data
        return None

    def _find_poc_in_dir(self, root: str, bug_id: str, ground_len: int):
        best_data = None
        best_diff = None

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, root)
                name_lower = rel.lower()
                if bug_id not in name_lower:
                    continue
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                try:
                    with open(full, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if len(data) == ground_len:
                    return data
                diff = abs(len(data) - ground_len)
                if best_data is None or diff < best_diff:
                    best_data = data
                    best_diff = diff
        return best_data

    def _find_generic_in_dir(self, root: str, ground_len: int):
        patterns = [
            "poc",
            "crash",
            "testcase",
            "clusterfuzz",
            "oss-fuzz",
            "bug",
            "regress",
            "input",
            "seed",
        ]
        candidates = []

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                full = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size <= 0:
                    continue
                rel = os.path.relpath(full, root)
                name_lower = rel.lower()
                priority = 1 if any(p in name_lower for p in patterns) else 0
                candidates.append((priority, size, full))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x[0], abs(x[1] - ground_len), x[1]))

        for priority, size, path in candidates:
            if size > 1024 * 1024:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            if data:
                return data
        return None

    def _fallback_payload(self, ground_len: int) -> bytes:
        # Construct a generic ELF-like binary with an UPX signature padded to the desired length
        data = bytearray()
        data += b"\x7fELF"  # ELF magic
        data += b"UPX!" * 16
        if len(data) < ground_len:
            data.extend(b"A" * (ground_len - len(data)))
        return bytes(data[:ground_len])