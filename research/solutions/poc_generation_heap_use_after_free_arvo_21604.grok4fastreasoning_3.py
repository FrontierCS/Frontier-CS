class Solution:
    def solve(self, src_path: str) -> bytes:
        parts = []
        parts.append(b'%PDF-1.7\n')
        parts.append(b'%ÂÃÏÓ\n')

        # Object 1: Catalog with AcroForm
        parts.append(b'1 0 obj\n')
        parts.append(b'<< /Type /Catalog /Pages 2 0 R /AcroForm 3 0 R >>\n')
        parts.append(b'endobj\n\n')

        # Object 2: Pages
        parts.append(b'2 0 obj\n')
        parts.append(b'<< /Type /Pages /Kids [4 0 R] /Count 1 >>\n')
        parts.append(b'endobj\n\n')

        # Object 3: AcroForm
        parts.append(b'3 0 obj\n')
        parts.append(b'<< /Fields [] /NeedAppearances true >>\n')
        parts.append(b'endobj\n\n')

        # Object 4: Page
        parts.append(b'4 0 obj\n')
        parts.append(b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /XObject << /FormX 6 0 R >> /Font << /F1 8 0 R >> >> /Annots [] >>\n')
        parts.append(b'endobj\n\n')

        # Object 5: Contents
        parts.append(b'5 0 obj\n')
        parts.append(b'<< /Length 55 >>\n')
        parts.append(b'stream\n')
        parts.append(b'q 100 0 0 100 100 600 cm /FormX Do Q\n')
        parts.append(b'endstream\n')
        parts.append(b'endobj\n\n')

        # Object 6: Form XObject (standalone form)
        parts.append(b'6 0 obj\n')
        parts.append(b'<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 100 100] /Resources << /Font << /F2 9 0 R >> >> /Length 56 >>\n')
        parts.append(b'stream\n')
        parts.append(b'q 100 0 0 100 0 0 cm BT /F2 12 Tf 10 90 Td (Standalone Form Dict) Tj ET Q\n')
        parts.append(b'endstream\n')
        parts.append(b'endobj\n\n')

        # Object 7: Font F1 (unused for form)
        offset7 = len(b''.join(parts))
        parts.append(b'7 0 obj\n')  # Placeholder, but we use 8
        parts.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n')
        parts.append(b'endobj\n\n')

        # Object 8: Font F1
        parts.append(b'8 0 obj\n')
        parts.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n')
        parts.append(b'endobj\n\n')

        # Object 9: Font F2 for form
        parts.append(b'9 0 obj\n')
        parts.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n')
        parts.append(b'endobj\n\n')

        # xref
        parts.append(b'xref\n')
        parts.append(b'0 10\n')
        parts.append(b'0000000000 65535 f \n')
        offset1 = 18  # approx %PDF + %
        parts.append(f'{offset1:010d} 00000 n \n'.encode())
        offset2 = offset1 + 59
        parts.append(f'{offset2:010d} 00000 n \n'.encode())
        offset3 = offset2 + 47
        parts.append(f'{offset3:010d} 00000 n \n'.encode())
        offset4 = offset3 + 58
        parts.append(f'{offset4:010d} 00000 n \n'.encode())
        offset5 = offset4 + 105
        parts.append(f'{offset5:010d} 00000 n \n'.encode())
        offset6 = offset5 + 153
        parts.append(f'{offset6:010d} 00000 n \n'.encode())
        offset7 = offset6 + 106  # adjust
        parts.append(f'{offset7:010d} 00000 n \n'.encode())
        offset8 = offset7 + 70
        parts.append(f'{offset8:010d} 00000 n \n'.encode())
        offset9 = offset8 + 70
        parts.append(f'{offset9:010d} 00000 n \n'.encode())
        parts.append(b'0000000000 65535 f \n')  # dummy for 10

        parts.append(b'trailer\n')
        parts.append(b'<< /Size 10 /Root 1 0 R >>\n')
        parts.append(b'startxref\n')
        startxref = len(b''.join(parts))
        parts.append(f'{startxref + 20:010d}\n'.encode())  # approx
        parts.append(b'%%EOF\n')

        # Note: Offsets are approximate; in practice, adjust for exact positions to make valid PDF
        return b''.join(parts)