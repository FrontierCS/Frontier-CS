import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.5\n'
        contents = b'BT /F1 12 Tf 100 700 Td (Hello World) Tj ET'
        len_c = len(contents)
        font_data = b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
        len_f = len(font_data)
        contents_data = b'<< /Length %d >>\nstream\n' % len_c + contents + b'\nendstream'
        len_cd = len(contents_data)
        len_index = 20
        for _ in range(10):
            off0 = len_index
            off1 = len_index + len_f
            index_str = f"5 {off0} 6 {off1}"
            index_bytes = index_str.encode('ascii')
            new_len = len(index_bytes)
            if new_len == len_index:
                break
            len_index = new_len
        stream_content = index_bytes + font_data + contents_data
        compressed = zlib.compress(stream_content)
        len_compr = len(compressed)
        first_pos = len(index_bytes)
        objstm_dict = b'<< /Type /ObjStm /N 2 /First %d /Length %d /Filter /FlateDecode >>\n' % (first_pos, len_compr)
        objstm = b'4 0 obj\n' + objstm_dict + b'stream\n' + compressed + b'endstream\nendobj\n'
        len_objstm = len(objstm)
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        len_obj1 = len(obj1)
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        len_obj2 = len(obj2)
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
        len_obj3 = len(obj3)
        off1 = len(header)
        off2 = off1 + len_obj1
        off3 = off2 + len_obj2
        off4 = off3 + len_obj3
        body = header + obj1 + obj2 + obj3 + objstm
        xref_start = len(body)
        xref = b'xref\n0 7\n0000000000 65535 f \n'
        xref += f'{off1:010d}'.encode() + b' 00000 n \n'
        xref += f'{off2:010d}'.encode() + b' 00000 n \n'
        xref += f'{off3:010d}'.encode() + b' 00000 n \n'
        xref += f'{off4:010d}'.encode() + b' 00000 n \n'
        xref += f'{off4:010d}'.encode() + b' 00000 o \n'
        xref += f'{off4:010d}'.encode() + b' 00001 o \n'
        trailer = b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n' + str(xref_start).encode() + b'\n%%EOF'
        return body + xref + trailer
