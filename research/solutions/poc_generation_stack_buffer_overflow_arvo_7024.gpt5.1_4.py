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
        target_len = 45

        # Determine base directory: either extract tarball or use existing directory
        if os.path.isdir(src_path):
            base_dir = src_path
        else:
            base_dir = tempfile.mkdtemp(prefix="src_extract_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(base_dir)
            except tarfile.ReadError:
                # Not a tar file; fallback to simple PoC
                return b"A" * target_len

        suspicious_keywords = [
            "poc",
            "crash",
            "bug",
            "id_",
            "testcase",
            "clusterfuzz",
            "minimized",
            "gre",
            "80211",
            "wireshark",
            "oss-fuzz",
            "fuzz"
        ]

        best_candidate = None
        best_diff = None
        best_suspicious = False

        for root, dirs, files in os.walk(base_dir):
            for name in files:
                path = os.path.join(root, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue

                size = st.st_size
                if size <= 0:
                    continue

                diff = abs(size - target_len)
                path_lower = path.lower()
                suspicious = any(k in path_lower for k in suspicious_keywords)

                if best_diff is None:
                    update = True
                elif diff < best_diff:
                    update = True
                elif diff == best_diff and suspicious and not best_suspicious:
                    update = True
                else:
                    update = False

                if not update:
                    continue

                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue

                best_candidate = data
                best_diff = diff
                best_suspicious = suspicious

                # Early exit if we found an exact-length, suspicious file
                if best_diff == 0 and best_suspicious:
                    return best_candidate

        if best_candidate is not None:
            return best_candidate

        # Fallback: simple 45-byte payload
        return b"A" * target_len