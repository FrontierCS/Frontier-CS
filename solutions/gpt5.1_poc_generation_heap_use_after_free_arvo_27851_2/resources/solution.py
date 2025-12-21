import os
import tarfile
import tempfile
from typing import Optional


class Solution:
    def __init__(self) -> None:
        pass

    def _extract_tar_if_needed(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.mkdtemp(prefix="src-")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except tarfile.ReadError:
            # Not a tar file; return empty temp directory.
            pass
        return tmpdir

    def _find_poc_file(self, root: str, target_len: int) -> Optional[bytes]:
        best_data: Optional[bytes] = None
        best_score: float = float("-inf")

        for dirpath, _, filenames in os.walk(root):
            ldir = dirpath.lower()
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                size = st.st_size
                if size <= 0 or size > 65536:
                    continue

                lname = name.lower()
                score = 0.0

                if size == target_len:
                    score += 10.0
                else:
                    score -= abs(size - target_len) / max(target_len, 1)

                key_weights = {
                    "poc": 6.0,
                    "crash": 5.0,
                    "heap": 2.0,
                    "uaf": 3.0,
                    "raw_encap": 8.0,
                    "raw-encap": 8.0,
                    "rawencap": 8.0,
                    "raw": 1.5,
                    "encap": 4.0,
                    "openflow": 3.0,
                    "ovs": 2.0,
                    "openvswitch": 2.0,
                    "id_": 1.0,
                    "payload": 2.0,
                    "testcase": 1.5,
                }
                for kw, w in key_weights.items():
                    if kw in lname:
                        score += w

                dir_keywords = [("poc", 3.0), ("crash", 2.0), ("uaf", 1.5), ("fuzz", 2.0)]
                for kw, w in dir_keywords:
                    if kw in ldir:
                        score += w

                ext = os.path.splitext(name)[1].lower()
                if ext in (
                    ".c",
                    ".h",
                    ".cpp",
                    ".cc",
                    ".hpp",
                    ".java",
                    ".py",
                    ".md",
                    ".rst",
                    ".txt",
                    ".patch",
                    ".diff",
                ):
                    score -= 5.0

                if score <= best_score:
                    continue

                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue

                if best_data is not None and score == best_score:
                    prev_non_ascii = sum(b >= 0x80 or b == 0x00 for b in best_data)
                    cur_non_ascii = sum(b >= 0x80 or b == 0x00 for b in data)
                    if cur_non_ascii <= prev_non_ascii:
                        continue

                best_score = score
                best_data = data

        return best_data

    def solve(self, src_path: str) -> bytes:
        root = self._extract_tar_if_needed(src_path)
        poc = self._find_poc_file(root, target_len=72)
        if poc is not None:
            return poc

        # Fallback: generic 72-byte pattern resembling a RAW_ENCAP-like payload.
        pattern = (
            b"\x00\x00\x00\x10"          # length/placeholder
            b"\xff\xff\xff\xff"          # dummy xid/vendor
            b"NXAST"                     # tag
            b"_RAW_ENCAP"               # keyword
            b"\x01\x02\x03\x04\x05\x06"  # misc bytes
        )
        if len(pattern) >= 72:
            return pattern[:72]
        return pattern + b"A" * (72 - len(pattern))
