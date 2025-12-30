class Solution:
    def solve(self, src_path: str) -> bytes:
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 2 >>
stream
Q
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000073 00000 n 
0000000122 00000 n 
0000000222 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
298
%%EOF"""
        return pdf_content