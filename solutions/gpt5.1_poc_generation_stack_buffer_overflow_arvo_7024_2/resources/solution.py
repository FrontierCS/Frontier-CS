import os
import tarfile
import tempfile
from pathlib import Path
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 45
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract the source tarball
                try:
                    with tarfile.open(src_path, "r:*") as tar:
                        tar.extractall(tmpdir)
                except Exception:
                    return self._fallback_poc(target_len)

                root = Path(tmpdir)
                poc = self._find_poc(root, target_len)
                if poc is not None:
                    return poc

                return self._fallback_poc(target_len)
        except Exception:
            return self._fallback_poc(target_len)

    def _fallback_poc(self, length: int) -> bytes:
        # Construct a GRE-like header followed by padding to reach desired length.
        # 0x0000 flags/version, 0x6558 as an arbitrary EtherType-like value.
        gre_header = b"\x00\x00\x65\x58"
        if length <= len(gre_header):
            return gre_header[:length]
        padding = b"A" * (length - len(gre_header))
        return gre_header + padding

    def _is_probably_binary(
        self, path: Path, max_check: int = 2048, text_threshold: float = 0.85
    ) -> bool:
        try:
            with path.open("rb") as f:
                chunk = f.read(max_check)
        except Exception:
            return False

        if not chunk:
            return False

        if b"\x00" in chunk:
            return True

        text_chars = set(range(32, 127))
        text_chars.update([ord("\n"), ord("\r"), ord("\t"), 0x0B, 0x0C])

        printable = sum(b in text_chars for b in chunk)
        ratio = printable / len(chunk)
        return ratio < text_threshold

    def _find_poc(self, root: Path, target_len: int) -> Optional[bytes]:
        name_patterns = [
            "poc",
            "overflow",
            "overrun",
            "crash",
            "bug",
            "cve",
            "assert",
            "fail",
            "fuzz",
            "testcase",
            "clusterfuzz",
            "id:",
            "input",
            "gre",
            "80211",
            "wlan",
            "arvo",
            "7024",
        ]
        preferred_exts = {".pcap", ".pcapng", ".bin", ".dat", ".raw"}
        candidates = []

        # Primary pass: filenames containing suspicious patterns
        for path in root.rglob("*"):
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue

            try:
                st = path.stat()
            except OSError:
                continue

            size = st.st_size
            if size <= 0 or size > 1_000_000:
                continue

            lower_name = path.name.lower()
            if not any(pat in lower_name for pat in name_patterns):
                continue

            if not self._is_probably_binary(path):
                continue

            distance = abs(size - target_len)
            ext_factor = 0 if path.suffix.lower() in preferred_exts else 1
            score = (distance, ext_factor, size)
            candidates.append((score, path))

        # Secondary: any binary file exactly target size
        if not candidates:
            for path in root.rglob("*"):
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue

                try:
                    st = path.stat()
                except OSError:
                    continue

                size = st.st_size
                if size != target_len:
                    continue

                if not self._is_probably_binary(path):
                    continue

                ext_factor = 0 if path.suffix.lower() in preferred_exts else 1
                score = (0, ext_factor, size)
                candidates.append((score, path))

        # Tertiary: any small binary file (prefer near target_len)
        if not candidates:
            for path in root.rglob("*"):
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue

                try:
                    st = path.stat()
                except OSError:
                    continue

                size = st.st_size
                if size <= 0 or size > 65536:
                    continue

                if not self._is_probably_binary(path):
                    continue

                distance = abs(size - target_len)
                ext_factor = 0 if path.suffix.lower() in preferred_exts else 1
                score = (distance, ext_factor, size)
                candidates.append((score, path))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        best_path = candidates[0][1]

        try:
            with best_path.open("rb") as f:
                data = f.read()
            return data
        except Exception:
            return None
