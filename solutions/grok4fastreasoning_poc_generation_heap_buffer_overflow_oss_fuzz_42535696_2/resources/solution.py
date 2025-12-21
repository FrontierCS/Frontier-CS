class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.4\n\n'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n'
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n\n'
        content = b'Q Q'
        length = len(content)
        obj4 = b'4 0 obj\n<< /Length ' + str(length).encode('ascii') + b' >>\nstream\n' + content + b'endstream\nendobj\n\n'
        body = header + obj1 + obj2 + obj3 + obj4
        pos1 = len(header)
        pos2 = pos1 + len(obj1)
        pos3 = pos2 + len(obj2)
        pos4 = pos3 + len(obj3)
        xref_start = len(body)
        xref = b'xref\n0 5\n0000000000 65535 f \n' + \
               f'{pos1:010d} 00000 n \n'.encode('ascii') + \
               f'{pos2:010d} 00000 n \n'.encode('ascii') + \
               f'{pos3:010d} 00000 n \n'.encode('ascii') + \
               f'{pos4:010d} 00000 n \n'.encode('ascii')
        trailer = b'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n' + \
                  f'{xref_start}\n%%EOF'.encode('ascii')
        pdf = body + xref + trailer
        return pdf
