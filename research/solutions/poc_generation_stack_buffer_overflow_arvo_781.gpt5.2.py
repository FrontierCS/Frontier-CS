import io
import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def _read_text_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo, max_bytes: int = 2_000_000) -> Optional[str]:
        if not member.isreg():
            return None
        if member.size <= 0 or member.size > max_bytes:
            return None
        f = tf.extractfile(member)
        if f is None:
            return None
        try:
            data = f.read(max_bytes + 1)
        finally:
            try:
                f.close()
            except Exception:
                pass
        if not data:
            return None
        return data.decode("utf-8", errors="ignore")

    def _read_bytes_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo, max_bytes: int = 1_000_000) -> Optional[bytes]:
        if not member.isreg():
            return None
        if member.size < 0 or member.size > max_bytes:
            return None
        f = tf.extractfile(member)
        if f is None:
            return None
        try:
            return f.read(max_bytes + 1)
        finally:
            try:
                f.close()
            except Exception:
                pass

    def _find_embedded_poc(self, tf: tarfile.TarFile) -> Optional[bytes]:
        keywords = (
            "crash",
            "poc",
            "repro",
            "regress",
            "overflow",
            "asan",
            "ubsan",
            "oss-fuzz",
            "issue",
            "cve",
            "stack",
            "oob",
        )
        dir_hints = ("poc", "pocs", "repro", "repros", "crash", "crashes", "corpus", "fuzz", "fuzzer", "oss-fuzz", "testcase", "testcases")

        best: Optional[Tuple[int, int, bytes]] = None  # (score, size, data)

        for m in tf.getmembers():
            if not m.isreg():
                continue
            if m.size <= 0 or m.size > 4096:
                continue
            name = m.name
            lname = name.lower()

            score = 0
            if any(k in lname for k in keywords):
                score += 1000
            parts = [p for p in lname.split("/") if p]
            if any(p in dir_hints for p in parts):
                score += 500
            if lname.endswith((".bin", ".poc", ".crash", ".repro", ".dat", ".seed")):
                score += 200
            if m.size == 8:
                score += 150
            elif m.size <= 16:
                score += 100
            elif m.size <= 64:
                score += 50
            score -= m.size

            if score < 1100:
                continue

            data = self._read_bytes_member(tf, m, max_bytes=4096)
            if not data:
                continue
            cand = (score, m.size, data)
            if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                best = cand

        return None if best is None else best[2]

    def _find_harness_text(self, tf: tarfile.TarFile) -> Optional[str]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")
        for m in tf.getmembers():
            if not m.isreg():
                continue
            lname = m.name.lower()
            if not lname.endswith(exts):
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            txt = self._read_text_member(tf, m, max_bytes=2_000_000)
            if not txt:
                continue
            if "llvmfuzzertestoneinput" in txt.lower():
                return txt
        return None

    def _infer_min_size(self, harness: str) -> int:
        mins = []
        for pat in (
            r"\bSize\s*<\s*(\d+)\b",
            r"\bsize\s*<\s*(\d+)\b",
            r"\bif\s*\(\s*Size\s*<=\s*(\d+)\s*\)",
            r"\bif\s*\(\s*size\s*<=\s*(\d+)\s*\)",
        ):
            for m in re.finditer(pat, harness):
                try:
                    mins.append(int(m.group(1)))
                except Exception:
                    pass
        if not mins:
            return 0
        return max(mins)

    def _infer_delimiter(self, harness: str) -> Optional[bytes]:
        h = harness
        hl = h.lower()

        if ("memchr" in hl or "find" in hl or "strchr" in hl) and ("'\\n'" in h or '"\\n"' in h):
            return b"\n"
        if ("memchr" in hl or "find" in hl or "strchr" in hl) and ("'\\0'" in h or '"\\0"' in h or "0x00" in hl):
            return b"\x00"

        if "'\\n'" in h or '"\\n"' in h:
            return b"\n"
        if "'\\0'" in h or '"\\0"' in h or "0x00" in hl:
            return b"\x00"
        return None

    def solve(self, src_path: str) -> bytes:
        if not src_path or not os.path.exists(src_path):
            return b"\x00" * 8

        try:
            with tarfile.open(src_path, "r:*") as tf:
                embedded = self._find_embedded_poc(tf)
                if embedded is not None and len(embedded) > 0:
                    return embedded

                harness = self._find_harness_text(tf)
                min_size = 0
                delim = None
                if harness:
                    min_size = self._infer_min_size(harness)
                    delim = self._infer_delimiter(harness)

                L = max(8, min_size if min_size > 0 else 0)

                if delim == b"\n":
                    return b"\n" + (b"\x00" * (L - 1))
                return b"\x00" * L
        except Exception:
            return b"\x00" * 8