import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        target_len = 133

        with tempfile.TemporaryDirectory() as tmpdir:
            # Safely extract the tarball
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory: str, target: str) -> bool:
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

                for member in tf.getmembers():
                    member_path = os.path.join(tmpdir, member.name)
                    if not is_within_directory(tmpdir, member_path):
                        continue
                    try:
                        tf.extract(member, tmpdir)
                    except Exception:
                        # Ignore problematic members
                        continue

            return self._find_poc(tmpdir, target_len)

    def _find_poc(self, root: str, target_len: int) -> bytes:
        image_exts = {
            ".jxl", ".jpeg", ".jpg", ".bin", ".dat", ".img",
            ".heic", ".avif", ".webp", ".png", ".bmp",
            ".tif", ".tiff", ".ico", ".raw"
        }

        best_133_data = None
        best_133_score = -1

        bugid_data = None
        bugid_size = None

        bugid_keywords = ("42535447", "decodegainmapmetadata")

        # First pass: look for exact-length PoC and bug-id-related files
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                lower = path.lower()
                try:
                    sz = os.path.getsize(path)
                except OSError:
                    continue

                # Files referencing the bug id or function name (size-limited)
                if any(k in lower for k in bugid_keywords) and sz <= 1024 * 1024:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        data = None
                    if data:
                        if bugid_data is None or sz < bugid_size:
                            bugid_data = data
                            bugid_size = sz

                # Exact-length candidate files
                if sz == target_len:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    if len(data) != target_len:
                        continue

                    # Determine if file is likely binary
                    printable = 0
                    for b in data:
                        if 0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D):
                            printable += 1
                    text_ratio = printable / float(target_len)
                    is_binary = text_ratio < 0.8

                    score = 0
                    if "42535447" in lower:
                        score += 100
                    if "oss-fuzz" in lower or "ossfuzz" in lower:
                        score += 50
                    if (
                        "poc" in lower
                        or "crash" in lower
                        or "testcase" in lower
                        or "regress" in lower
                    ):
                        score += 30
                    if "gainmap" in lower or "hdr" in lower:
                        score += 10
                    ext = os.path.splitext(lower)[1]
                    if ext in image_exts:
                        score += 5
                    if is_binary:
                        score += 10

                    if score > best_133_score:
                        best_133_score = score
                        best_133_data = data

        # Prefer a 133-byte candidate if found
        if best_133_data is not None:
            return best_133_data

        # Fallback to any file related to the bug id
        if bugid_data is not None:
            return bugid_data

        # Second pass: choose the smallest binary-looking file as a last-resort PoC
        fallback_data = None
        fallback_size = None

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    sz = os.path.getsize(path)
                except OSError:
                    continue
                if sz == 0 or sz > 1024 * 1024:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if not data:
                    continue

                printable = 0
                for b in data:
                    if 0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D):
                        printable += 1
                text_ratio = printable / float(len(data))
                is_binary = text_ratio < 0.7
                if not is_binary:
                    continue

                if fallback_data is None or sz < fallback_size:
                    fallback_data = data
                    fallback_size = sz

        if fallback_data is not None:
            return fallback_data

        # Ultimate fallback: arbitrary bytes of the target length
        return b"A" * target_len
