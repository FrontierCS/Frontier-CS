class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.4\n'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n'
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n'
        stream_dict = b'4 0 obj\n<< /Length 2 >>\nstream\n'
        stream_content = b'Q'
        stream_end = b'\nendstream\nendobj\n\n'
        body = [header, obj1, obj2, obj3, stream_dict, stream_content, stream_end]
        pdf_bytes = b''.join(body)
        pos1 = len(header)
        pos2 = pos1 + len(obj1)
        pos3 = pos2 + len(obj2)
        pos4 = pos3 + len(obj3)
        xref_start = len(pdf_bytes)
        def pos_str(p):
            return f'{p:010d}'.encode()
        xref = (b'xref\n0 5\n0000000000 65535 f \n' +
                pos_str(pos1) + b' 00000 n \n' +
                pos_str(pos2) + b' 00000 n \n' +
                pos_str(pos3) + b' 00000 n \n' +
                pos_str(pos4) + b' 00000 n \n' +
                b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n' +
                f'{xref_start}\n'.encode() +
                b'%%EOF')
        return pdf_bytes + xref