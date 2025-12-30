import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        objects = {}

        # 1: Catalog
        objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"

        # 2: Pages
        objects[2] = b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>"

        # 3: Page
        objects[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] /Resources << >> /Contents 4 0 R >>"

        # 4: Contents with a matched q/Q to trigger restore of viewer state
        stream_data = b"q\nQ\n"
        stream_dict = b"<< /Length " + str(len(stream_data)).encode("ascii") + b" >>"
        objects[4] = stream_dict + b"\nstream\n" + stream_data + b"endstream"

        # Assemble PDF
        doc = bytearray()
        doc.extend(header)

        offsets = {0: 0}
        for obj_id in sorted(objects.keys()):
            offsets[obj_id] = len(doc)
            doc.extend(f"{obj_id} 0 obj\n".encode("ascii"))
            doc.extend(objects[obj_id])
            doc.extend(b"\nendobj\n")

        startxref = len(doc)
        xref_entries = len(objects) + 1  # include object 0
        doc.extend(b"xref\n")
        doc.extend(f"0 {xref_entries}\n".encode("ascii"))
        doc.extend(b"0000000000 65535 f \n")
        for obj_id in sorted(objects.keys()):
            off = offsets[obj_id]
            doc.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        doc.extend(b"trailer\n")
        doc.extend(b"<< ")
        doc.extend(f"/Size {xref_entries} ".encode("ascii"))
        doc.extend(b"/Root 1 0 R ")
        doc.extend(b">>\n")
        doc.extend(b"startxref\n")
        doc.extend(f"{startxref}\n".encode("ascii"))
        doc.extend(b"%%EOF\n")

        return bytes(doc)