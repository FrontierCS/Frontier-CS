import os
import re
import tarfile
import zipfile
from typing import Iterable, List, Optional, Tuple


class Solution:
    def _iter_archive_text_files(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".inc", ".inl", ".y", ".yy", ".l", ".rl",
            ".cmake", ".gn", ".gni", ".bzl", ".bazel",
            "makefile", "dockerfile",
        }

        def want(name: str) -> bool:
            base = os.path.basename(name).lower()
            if base in exts:
                return True
            _, ext = os.path.splitext(base)
            if ext in exts:
                return True
            if base.endswith((".cmake", ".gn", ".gni", ".bzl", ".bazel")):
                return True
            return False

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    rel = os.path.relpath(path, src_path)
                    if not want(rel):
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read(256 * 1024)
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    yield rel, text
            return

        lower = src_path.lower()
        if lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(src_path, "r") as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        name = info.filename
                        if not want(name):
                            continue
                        try:
                            data = zf.read(info, pwd=None)[: 256 * 1024]
                            text = data.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
                        yield name, text
            except Exception:
                return
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    if not want(name):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(256 * 1024)
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    yield name, text
        except Exception:
            return

    def _extract_fuzzer_hints(self, files: Iterable[Tuple[str, str]]) -> Tuple[int, List[bytes], bool, bool]:
        min_size = 0
        required_prefixes: List[bytes] = []
        saw_http = False
        saw_https = False
        saw_fgets_or_line = False

        re_min = re.compile(r"\bif\s*\(\s*Size\s*<\s*(\d+)\s*\)\s*return\b")
        re_memcmp = re.compile(r"\bmemcmp\s*\(\s*Data\s*,\s*\"([^\"]*)\"\s*,\s*(\d+)\s*\)")
        re_strncmp = re.compile(r"\bstrncmp\s*\(\s*\(?\s*(?:const\s+)?char\s*\*\s*\)?\s*Data\s*,\s*\"([^\"]*)\"\s*,\s*(\d+)\s*\)")
        re_data0eq = re.compile(r"\bData\s*\[\s*0\s*\]\s*==\s*'([^']*)'")

        for _, text in files:
            if "http://" in text:
                saw_http = True
            if "https://" in text:
                saw_https = True
            if ("fgets(" in text) or ("getline(" in text) or ("getdelim(" in text) or ("scanf(" in text) or ("sscanf(" in text):
                saw_fgets_or_line = True

            if "LLVMFuzzerTestOneInput" not in text:
                continue

            for m in re_min.finditer(text):
                try:
                    n = int(m.group(1))
                    if n > min_size:
                        min_size = n
                except Exception:
                    pass

            for m in re_memcmp.finditer(text):
                s = m.group(1)
                try:
                    n = int(m.group(2))
                except Exception:
                    continue
                b = s.encode("latin-1", errors="ignore")[:n]
                if b:
                    required_prefixes.append(b)

            for m in re_strncmp.finditer(text):
                s = m.group(1)
                try:
                    n = int(m.group(2))
                except Exception:
                    continue
                b = s.encode("latin-1", errors="ignore")[:n]
                if b:
                    required_prefixes.append(b)

            for m in re_data0eq.finditer(text):
                ch = m.group(1)
                if ch:
                    required_prefixes.append(ch.encode("latin-1", errors="ignore")[:1])

        return min_size, required_prefixes, saw_http or saw_https, saw_fgets_or_line

    def solve(self, src_path: str) -> bytes:
        files = list(self._iter_archive_text_files(src_path))
        min_size, required_prefixes, saw_httpish, saw_line_input = self._extract_fuzzer_hints(files)

        payload_len = 9

        base: bytes
        if saw_httpish:
            base = b"http://A\n"
        else:
            base = b"A" * 8 + (b"\n" if saw_line_input else b"A")

        base = base[:payload_len].ljust(payload_len, b"A")

        if required_prefixes:
            best = max((p for p in required_prefixes if len(p) <= payload_len), key=len, default=b"")
            if best:
                p = best
                rest_len = payload_len - len(p)
                if saw_line_input and rest_len > 0:
                    rest = (b"A" * (rest_len - 1)) + b"\n"
                else:
                    rest = b"A" * rest_len
                base = p + rest

        if min_size <= payload_len:
            return base

        # If the harness requires larger input, extend minimally while keeping a newline at end if line-based.
        ext_len = min_size - payload_len
        if saw_line_input:
            if base.endswith(b"\n"):
                return base[:-1] + (b"A" * ext_len) + b"\n"
            return base + (b"A" * (ext_len - 1)) + b"\n" if ext_len > 0 else base
        return base + (b"A" * ext_len)