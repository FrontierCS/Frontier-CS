import os
import re
import tarfile
from typing import Iterable, Optional, Tuple


def _c_unescape(s: str) -> bytes:
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch != "\\":
            out.append(ord(ch) & 0xFF)
            i += 1
            continue
        i += 1
        if i >= n:
            out.append(ord("\\"))
            break
        esc = s[i]
        i += 1

        if esc == "n":
            out.append(0x0A)
        elif esc == "r":
            out.append(0x0D)
        elif esc == "t":
            out.append(0x09)
        elif esc == "v":
            out.append(0x0B)
        elif esc == "b":
            out.append(0x08)
        elif esc == "f":
            out.append(0x0C)
        elif esc == "a":
            out.append(0x07)
        elif esc == "\\":
            out.append(0x5C)
        elif esc == "'":
            out.append(0x27)
        elif esc == '"':
            out.append(0x22)
        elif esc == "x":
            hx = ""
            if i < n and s[i] in "0123456789abcdefABCDEF":
                hx += s[i]
                i += 1
            if i < n and s[i] in "0123456789abcdefABCDEF":
                hx += s[i]
                i += 1
            if hx:
                out.append(int(hx, 16) & 0xFF)
            else:
                out.append(ord("x"))
        elif esc in "01234567":
            octs = esc
            for _ in range(2):
                if i < n and s[i] in "01234567":
                    octs += s[i]
                    i += 1
                else:
                    break
            out.append(int(octs, 8) & 0xFF)
        else:
            out.append(ord(esc) & 0xFF)
    return bytes(out)


def _iter_source_files_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp")
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(exts):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
                if st.st_size > 1_000_000:
                    continue
                with open(p, "rb") as f:
                    yield p, f.read(1_000_000)
            except OSError:
                continue


def _iter_source_files_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".ipp")
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not name.endswith(exts):
                    continue
                if m.size <= 0 or m.size > 1_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    with f:
                        yield name, f.read(1_000_000)
                except Exception:
                    continue
    except Exception:
        return


def _analyze_fuzzer_sources(files: Iterable[Tuple[str, bytes]]) -> Tuple[int, Optional[bytes]]:
    re_fuzzer = re.compile(r"(LLVMFuzzerTestOneInput|FuzzedDataProvider)")
    re_size_cond1 = re.compile(r"\bSize\s*([<]=?)\s*(\d+)\b")
    re_size_cond2 = re.compile(r"\bsize\s*([<]=?)\s*(\d+)\b")
    re_memcmp = re.compile(
        r'\bmemcmp\s*\(\s*(?:Data|data)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*(\d+)\s*\)'
    )
    re_strncmp = re.compile(
        r'\bstrncmp\s*\(\s*(?:\(\s*const\s+char\s*\*\s*\)\s*)?(?:Data|data)\s*,\s*"((?:[^"\\]|\\.)*)"\s*,\s*(\d+)\s*\)'
    )
    re_starts = re.compile(r'\.starts_with\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)')

    min_required = 0
    best_magic: Optional[bytes] = None

    for path, data in files:
        try:
            txt = data.decode("utf-8", "ignore")
        except Exception:
            continue

        if not re_fuzzer.search(txt):
            continue

        for rx in (re_size_cond1, re_size_cond2):
            for m in rx.finditer(txt):
                op = m.group(1)
                val = int(m.group(2))
                if val < 0 or val > 1_000_000:
                    continue
                if op == "<":
                    req = val
                elif op == "<=":
                    req = val + 1
                else:
                    continue
                if req > min_required:
                    min_required = req

        for rx in (re_memcmp, re_strncmp):
            for m in rx.finditer(txt):
                lit = m.group(1)
                n = int(m.group(2))
                if n <= 0 or n > 64:
                    continue
                raw = _c_unescape(lit)
                if len(raw) >= n:
                    magic = raw[:n]
                else:
                    magic = raw + (b"A" * (n - len(raw)))
                if best_magic is None or len(magic) < len(best_magic):
                    best_magic = magic

        for m in re_starts.finditer(txt):
            raw = _c_unescape(m.group(1))
            if not raw or len(raw) > 64:
                continue
            if best_magic is None or len(raw) < len(best_magic):
                best_magic = raw

    if min_required > 4096:
        min_required = 0
    return min_required, best_magic


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_len = 9
        min_required = 0
        prefix: Optional[bytes] = None

        if os.path.isdir(src_path):
            min_required, prefix = _analyze_fuzzer_sources(_iter_source_files_from_dir(src_path))
        elif tarfile.is_tarfile(src_path):
            min_required, prefix = _analyze_fuzzer_sources(_iter_source_files_from_tar(src_path))

        L = base_len
        if min_required > L:
            L = min_required
        if prefix is not None and len(prefix) > L:
            L = len(prefix)

        if prefix is None:
            return b"A" * L
        if len(prefix) == L:
            return prefix
        return prefix + (b"A" * (L - len(prefix)))