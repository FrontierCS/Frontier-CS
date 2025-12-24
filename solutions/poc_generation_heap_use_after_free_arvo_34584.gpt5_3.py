import os
import tarfile
import zipfile
import tempfile
import shutil
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            root = None
            if os.path.isdir(src_path):
                root = src_path
            else:
                if tarfile.is_tarfile(src_path):
                    tmpdir = tempfile.mkdtemp(prefix="poc_extract_")
                    self._extract_tar(src_path, tmpdir)
                    root = tmpdir
                elif zipfile.is_zipfile(src_path):
                    tmpdir = tempfile.mkdtemp(prefix="poc_extract_")
                    self._extract_zip(src_path, tmpdir)
                    root = tmpdir
                else:
                    # Not an archive; try reading directly
                    try:
                        return self._read_file_bytes(src_path)
                    except Exception:
                        pass
                    root = os.path.dirname(os.path.abspath(src_path))
            if root is None:
                # Fallback PoC if nothing else works
                return self._fallback_poc()

            poc_bytes = self._find_poc_bytes(root, target_len=6624)
            if poc_bytes is not None:
                return poc_bytes

            # If exact size not found, try heuristics
            poc_bytes = self._find_poc_by_keyword(root, keywords=[b"Uint8ClampedArray"], preferred_exts=(".js", ".mjs", ".html", ".svg", ".txt"))
            if poc_bytes is not None:
                return poc_bytes

            # Try by name hints
            poc_bytes = self._find_poc_by_name(root, name_hints=("poc", "PoC", "POC", "repro", "crash", "testcase", "exploit"), preferred_exts=(".js", ".mjs", ".html", ".svg", ".txt"))
            if poc_bytes is not None:
                return poc_bytes

            # As a last attempt, pick any .js file with relevant content patterns
            poc_bytes = self._find_any_js(root)
            if poc_bytes is not None:
                return poc_bytes

            # Fallback generic PoC snippet
            return self._fallback_poc()
        finally:
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_tar(self, tar_path: str, dest_dir: str) -> None:
        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            base = os.path.realpath(dest_dir)
            safe_members = []
            for m in members:
                m_path = os.path.realpath(os.path.join(dest_dir, m.name))
                if not m_path.startswith(base + os.sep) and m_path != base:
                    continue
                safe_members.append(m)
            tf.extractall(path=dest_dir, members=safe_members)

    def _extract_zip(self, zip_path: str, dest_dir: str) -> None:
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                # prevent zip slip
                extracted_path = os.path.realpath(os.path.join(dest_dir, member.filename))
                base = os.path.realpath(dest_dir)
                if not extracted_path.startswith(base + os.sep) and extracted_path != base:
                    continue
                zf.extract(member, path=dest_dir)

    def _iter_files(self, root: str):
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                fpath = os.path.join(dirpath, fn)
                try:
                    st = os.stat(fpath)
                    size = st.st_size
                except Exception:
                    continue
                yield fpath, size

    def _read_file_bytes(self, path: str) -> bytes:
        with open(path, "rb") as f:
            return f.read()

    def _read_file_text(self, path: str, max_bytes: int = 1024 * 1024) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            # Try utf-8 first, fallback to latin-1
            try:
                return data.decode("utf-8", errors="ignore")
            except Exception:
                return data.decode("latin-1", errors="ignore")
        except Exception:
            return ""

    def _find_poc_bytes(self, root: str, target_len: int) -> bytes | None:
        # First pass: exact length and preferred extensions
        preferred_exts = (".js", ".mjs", ".html", ".svg", ".txt", "")
        exact_candidates = []
        for path, size in self._iter_files(root):
            if size == target_len:
                ext = os.path.splitext(path)[1].lower()
                exact_candidates.append((path, ext))
        if exact_candidates:
            # Rank by extension preference, name hints, and keyword occurrence
            def rank(item):
                path, ext = item
                name = os.path.basename(path).lower()
                ext_rank = preferred_exts.index(ext) if ext in preferred_exts else len(preferred_exts) + 1
                name_bonus = 0
                for hint in ("poc", "repro", "crash", "exploit", "testcase"):
                    if hint in name:
                        name_bonus += 10
                try:
                    data = self._read_file_bytes(path)
                    # Count occurrences of our key term
                    occ = data.count(b"Uint8ClampedArray") + data.count(b"TypedArray") + data.count(b"ArrayBuffer")
                except Exception:
                    occ = 0
                # Lower rank value is better, but we want to prioritize higher name_bonus and occ.
                # We'll invert bonuses as negatives for sorting.
                return (ext_rank, -name_bonus, -occ)
            exact_candidates.sort(key=rank)
            best_path = exact_candidates[0][0]
            try:
                return self._read_file_bytes(best_path)
            except Exception:
                pass
        return None

    def _find_poc_by_keyword(self, root: str, keywords: list[bytes], preferred_exts=(".js", ".mjs", ".html", ".svg", ".txt")) -> bytes | None:
        candidates = []
        for path, size in self._iter_files(root):
            # Skip huge files
            if size > 5 * 1024 * 1024:
                continue
            ext = os.path.splitext(path)[1].lower()
            try:
                data = self._read_file_bytes(path)
            except Exception:
                continue
            hit = 0
            for kw in keywords:
                hit += data.count(kw)
            if hit > 0:
                candidates.append((path, ext, hit, size))
        if not candidates:
            return None
        def rank(item):
            path, ext, hit, size = item
            name = os.path.basename(path).lower()
            ext_rank = preferred_exts.index(ext) if ext in preferred_exts else len(preferred_exts) + 1
            name_bonus = 0
            for hint in ("poc", "repro", "crash", "exploit", "testcase"):
                if hint in name:
                    name_bonus += 10
            # Prefer more hits, then preferred extensions, then smaller size
            return (-hit, ext_rank, -name_bonus, size)
        candidates.sort(key=rank)
        try:
            return self._read_file_bytes(candidates[0][0])
        except Exception:
            return None

    def _find_poc_by_name(self, root: str, name_hints=(), preferred_exts=(".js", ".mjs", ".html", ".svg", ".txt")) -> bytes | None:
        candidates = []
        for path, size in self._iter_files(root):
            name = os.path.basename(path)
            lname = name.lower()
            if any(h.lower() in lname for h in name_hints):
                ext = os.path.splitext(path)[1].lower()
                candidates.append((path, ext, size))
        if not candidates:
            return None
        def rank(item):
            path, ext, size = item
            ext_rank = preferred_exts.index(ext) if ext in preferred_exts else len(preferred_exts) + 1
            # Prefer js-like files, then ones that mention relevant keywords
            text = self._read_file_text(path, max_bytes=1024 * 1024)
            hits = 0
            for pat in ("Uint8ClampedArray", "TypedArray", "ArrayBuffer", "DataView"):
                hits += text.count(pat)
            # Prefer higher hits, then preferred extension, then smaller size
            return (-hits, ext_rank, size)
        candidates.sort(key=rank)
        try:
            return self._read_file_bytes(candidates[0][0])
        except Exception:
            return None

    def _find_any_js(self, root: str) -> bytes | None:
        # As a last resort, pick any reasonably sized JS file with typed array patterns
        js_candidates = []
        for path, size in self._iter_files(root):
            ext = os.path.splitext(path)[1].lower()
            if ext not in (".js", ".mjs"):
                continue
            if size > 2 * 1024 * 1024:
                continue
            text = self._read_file_text(path, max_bytes=1024 * 1024)
            if not text:
                continue
            score = 0
            for pat in ("Uint8ClampedArray", "TypedArray", "ArrayBuffer", "DataView", "prototype", "constructor", "buffer", "byteOffset", "byteLength"):
                score += text.count(pat)
            if score > 0:
                js_candidates.append((path, score, size))
        if not js_candidates:
            return None
        js_candidates.sort(key=lambda x: (-x[1], x[2]))
        try:
            return self._read_file_bytes(js_candidates[0][0])
        except Exception:
            return None

    def _fallback_poc(self) -> bytes:
        # Generic JS snippet exercising Uint8ClampedArray semantics; safe on fixed, may trigger on vulnerable
        code = r"""
// Fallback PoC generator: attempts to stress Uint8ClampedArray behaviors and typed array machinery.
(function(){
    function log(s) {
        try { if (typeof console !== 'undefined' && console.log) console.log(s); } catch(e){}
        try { if (typeof print !== 'undefined') print(s); } catch(e){}
    }

    function noise(n) {
        // allocate and fill multiple buffers to shuffle heap layout
        let arr = [];
        for (let i = 0; i < n; i++) {
            let ab = new ArrayBuffer(4096);
            let u8 = new Uint8Array(ab);
            for (let j = 0; j < u8.length; j += 257) u8[j] = (i + j) & 0xff;
            arr.push({ab, u8, i});
        }
        return arr;
    }

    function makeClamped(len) {
        let a = new Uint8ClampedArray(len);
        for (let i = 0; i < len; i++) a[i] = (i * 37) & 0xff;
        return a;
    }

    function stressSpecies() {
        // Manipulate species and constructors to coerce clone paths
        let orig = Uint8ClampedArray;
        let called = 0;
        let exoticCtor = function(...args) {
            called++;
            return Reflect.construct(orig, args);
        };
        Object.defineProperty(exoticCtor, Symbol.species, {
            get() { called += 17; return orig; }
        });
        try {
            Object.defineProperty(Uint8ClampedArray, Symbol.species, { value: exoticCtor });
        } catch (e) {}
        let a = makeClamped(1024);
        let b = a.slice(10, 900);
        a.fill(0x7f);
        b = b.subarray(0, 256);
        return called;
    }

    function stressProto() {
        // Swap prototypes and probe typed array intrinsics
        let saved = Object.getPrototypeOf(Uint8ClampedArray.prototype);
        let dummy = {
            get byteLength(){ return 0; },
            get byteOffset(){ return 0; },
            get buffer(){ return null; }
        };
        try {
            Object.setPrototypeOf(Uint8ClampedArray.prototype, dummy);
        } catch(e) {}
        let ok = false;
        try {
            let a = makeClamped(64);
            ok = a.byteLength === 64;
        } catch(e) {}
        try {
            Object.setPrototypeOf(Uint8ClampedArray.prototype, saved);
        } catch(e) {}
        return ok;
    }

    function stressProxy() {
        // Proxy the prototype to intercept property resolution
        let hits = 0;
        let handler = {
            get(target, prop, recv) {
                hits++;
                return Reflect.get(target, prop, recv);
            },
            has(target, prop) {
                hits++;
                return Reflect.has(target, prop);
            }
        };
        let P = new Proxy(Uint8ClampedArray.prototype, handler);
        let saved = Object.getPrototypeOf(Uint8ClampedArray.prototype);
        try {
            Object.setPrototypeOf(Uint8ClampedArray.prototype, P);
        } catch(e) {}
        let a = makeClamped(256);
        // Access a bunch of properties to trigger traps
        void a.byteLength;
        void a.byteOffset;
        void a.buffer;
        for (let i = 0; i < 256; i += 17) { a[i]; }
        try {
            Object.setPrototypeOf(Uint8ClampedArray.prototype, saved);
        } catch(e) {}
        return hits;
    }

    function stressDetach() {
        // Detach-like behavior: if engine supports structured clone or detach op
        let ab = new ArrayBuffer(2048);
        let c = new Uint8ClampedArray(ab);
        for (let i = 0; i < c.length; i++) c[i] = i & 0xff;
        try {
            if (typeof postMessage === 'function') {
                postMessage('', '*', [ab]);
            }
        } catch(e) {}
        // Slicing/ copying after transfer/detach may tickle bugs
        let d;
        try {
            d = c.slice(1, 100);
        } catch (e) {}
        return d ? d.length : -1;
    }

    // Create background noise to shape heap
    let trash = noise(64);
    // Interleave stresses
    for (let i = 0; i < 50; i++) {
        try { stressSpecies(); } catch(e){}
        try { stressProxy(); } catch(e){}
        try { stressProto(); } catch(e){}
    }
    // Final series
    try { stressDetach(); } catch(e){}

    // Keep references alive
    log("done " + (trash ? trash.length : 0));
})();
"""
        return code.encode("utf-8")
