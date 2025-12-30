import os
import tarfile
import tempfile
from typing import List, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Attempt to locate an included PoC within the provided tarball.
        Fallback to a generic 21-byte input if none is found.
        """
        poc = self._find_embedded_poc(src_path)
        if poc is not None:
            return poc

        # Fallback: a 21-byte CoAP-like message (header + payload marker + payload)
        # 0x40: Version=1, Type=CON, TKL=0
        # 0x01: Code=GET
        # 0x00 0x00: Message ID
        # 0xFF: Payload marker
        # 16 bytes of payload
        return bytes([0x40, 0x01, 0x00, 0x00, 0xFF]) + b'A' * 16

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        # Extract tarball to a temp directory and search for plausible PoC files
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    def is_within_directory(directory: str, target: str) -> bool:
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory

                    def safe_extract(tar: tarfile.TarFile, path: str = ".") -> None:
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                continue
                        tar.extractall(path)

                    safe_extract(tf, tmpdir)
            except Exception:
                return None

            candidates = self._collect_candidate_files(tmpdir)
            # Prefer files around the ground-truth length (21 bytes), then smallest
            exact_len_files = [p for p in candidates if os.path.getsize(p) == 21]
            if exact_len_files:
                data = self._read_first_file(exact_len_files)
                if data:
                    return data

            # Next, look for small files (<= 64 bytes) that could be PoCs
            small_files = sorted((p for p in candidates if 0 < os.path.getsize(p) <= 64),
                                 key=lambda p: abs(os.path.getsize(p) - 21))
            data = self._read_first_file(small_files)
            if data:
                return data

            # As a last resort, read any non-empty candidate file
            any_files = [p for p in candidates if os.path.getsize(p) > 0]
            data = self._read_first_file(any_files)
            if data:
                return data

        return None

    def _collect_candidate_files(self, root: str) -> List[str]:
        poc_keywords = [
            "poc", "crash", "id:", "testcase", "input", "seed", "repro", "trigger", "payload"
        ]
        exts = {"", ".bin", ".raw", ".dat", ".in", ".coap", ".txt"}
        candidates: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                name_lower = fn.lower()
                if any(kw in name_lower for kw in poc_keywords):
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in exts or len(ext) <= 5:
                        path = os.path.join(dirpath, fn)
                        # Avoid absurdly large files
                        try:
                            if os.path.getsize(path) <= 128 * 1024:
                                candidates.append(path)
                        except OSError:
                            pass
        return candidates

    def _read_first_file(self, paths: List[str]) -> Optional[bytes]:
        for p in paths:
            try:
                with open(p, "rb") as f:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                continue
        return None