class Solution:
    def solve(self, src_path: str) -> bytes:
        objects = [
            '<< /Type /Catalog /Pages 2 0 R /AcroForm 3 0 R >>',
            '<< /Type /Pages /Kids [4 0 R] /Count 1 >>',
            '<< /Fields [5 0 R] /DR 6 0 R /NeedAppearances true >>',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 7 0 R /Resources << /Font << /Helv 8 0 R >> /DR 6 0 R >> /Annots [5 0 R] >>',
            '<< /T (testfield) /Type /Annot /Subtype /Widget /Rect [100 100 200 120] /F 4 /DA (/Helv 12 Tf 0 g) /FT /Tx /Ff 0 >>',
            '<< /Font << /Helv 8 0 R >> >>',
            None,
            '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
        ]
        stream_content = 'BT\n100 700 Td\n(Hello World) Tj\nET\n'
        stream_len = len(stream_content)
        objects[6] = f"<< /Length {stream_len} >>\nstream\n{stream_content}endstream"
        header = "%PDF-1.4\n\n"
        body_parts = []
        current_offset = len(header)
        offsets = [0] * 9
        for i in range(1, 9):
            content = objects[i-1]
            obj_header = f"{i} 0 obj\n"
            obj_footer = "endobj\n"
            obj_str = obj_header + content + obj_footer
            obj_bytes = obj_str.encode('latin1')
            offsets[i] = current_offset
            body_parts.append(obj_bytes)
            current_offset += len(obj_bytes)
        xref_start = current_offset
        num_objs = 8
        xref = f"xref\n0 {num_objs}\n0000000000 65535 f \n".encode('latin1')
        for off in offsets[1:]:
            xref += f"{off:010d} 00000 n \n".encode('latin1')
        trailer = f"trailer\n<< /Size {num_objs} /Root 1 0 R >>\n".encode('latin1')
        startxref_line = f"startxref\n{xref_start}\n%%EOF".encode('latin1')
        pdf = header.encode('latin1') + b''.join(body_parts) + xref + trailer + startxref_line
        return pdf