import os
import re
import tarfile
from typing import Iterable, List, Optional, Tuple


class Solution:
    def _iter_text_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx",
            ".h", ".hh", ".hpp", ".hxx",
            ".m", ".mm",
            ".rs", ".go", ".java", ".py",
            ".txt", ".md",
        }
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                    if st.st_size > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue

    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx",
            ".h", ".hh", ".hpp", ".hxx",
            ".m", ".mm",
            ".rs", ".go", ".java", ".py",
            ".txt", ".md",
        }
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _collect_harness_sources(self, src_path: str) -> List[Tuple[str, str]]:
        files: List[Tuple[str, bytes]] = []
        if os.path.isdir(src_path):
            files = list(self._iter_text_files_from_dir(src_path))
        else:
            files = list(self._iter_text_files_from_tar(src_path))

        harnesses: List[Tuple[str, str]] = []
        for path, raw in files:
            try:
                txt = raw.decode("utf-8", "ignore")
            except Exception:
                continue
            if "LLVMFuzzerTestOneInput" in txt:
                harnesses.append((path, txt))
        return harnesses

    def _score_harness(self, txt: str) -> int:
        score = 0
        for kw in ("ovector", "ovec", "pcre", "pcre2", "match_data", "substitute"):
            score += txt.lower().count(kw)
        score += 5 * txt.count("LLVMFuzzerTestOneInput")
        return score

    def _choose_poc(self, harness_txt: str) -> bytes:
        zeros8 = b"\x00" * 8
        nul_delim8 = b"a\x00a\x00" + (b"\x00" * 4)
        nl_delim8 = b"a\na" + (b"\x00" * 5)

        t = harness_txt

        # Prefer length-prefix / integral-consuming formats.
        if re.search(r"\bConsumeIntegral\s*<\s*size_t\s*>", t) or re.search(r"\bConsumeIntegral\s*\(\s*\)", t):
            return zeros8
        if re.search(r"\bConsumeIntegral\s*<\s*uint64_t\s*>", t) or re.search(r"\bConsumeIntegral\s*<\s*unsigned\s+long\s+long\s*>", t):
            return zeros8
        if re.search(r"\bsize\s*<\s*8\b", t) and (("uint32_t" in t) or ("uint64_t" in t)):
            return zeros8
        if re.search(r"data\s*\+\s*4", t) and ("uint32_t" in t or "uint64_t" in t):
            return zeros8
        if "reinterpret_cast" in t and ("data" in t) and ("uint32_t" in t or "uint64_t" in t):
            return zeros8

        # Delimiter-based formats.
        if re.search(r"memchr\s*\([^;]*'\\0'|memchr\s*\([^;]*\b0\b", t) or ("'\\0'" in t) or ("\"\\0\"" in t):
            return nul_delim8
        if re.search(r"memchr\s*\([^;]*'\\n'|strchr\s*\([^;]*'\\n'|find\s*\(\s*'\\n'\s*\)", t) or ("'\\n'" in t) or ("\"\\n\"" in t):
            return nl_delim8

        return zeros8

    def solve(self, src_path: str) -> bytes:
        harnesses = self._collect_harness_sources(src_path)
        if not harnesses:
            return b"\x00" * 8

        best_path, best_txt = max(harnesses, key=lambda it: self._score_harness(it[1]))
        _ = best_path
        return self._choose_poc(best_txt)