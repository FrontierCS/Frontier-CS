class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'%PDF-1.7\n\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000053 00000 n \n0000000107 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n172\n%%EOF'
        return poc