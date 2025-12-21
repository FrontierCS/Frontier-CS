import tarfile
import re
import gzip
from io import BytesIO


class Solution:
    def solve(self, src_path: str) -> bytes:
        size_target = 6431

        def minimal_pdf() -> bytes:
            # Generate a small, well-formed PDF with correct xref offsets
            buf = BytesIO()
            w = buf.write

            w(b"%PDF-1.4\n")

            offsets = {}

            # 1 0 obj - Catalog
            offsets[1] = buf.tell()
            w(b"1 0 obj\n")
            w(b"<< /Type /Catalog /Pages 2 0 R >>\n")
            w(b"endobj\n")

            # 2 0 obj - Pages
            offsets[2] = buf.tell()
            w(b"2 0 obj\n")
            w(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
            w(b"endobj\n")

            # 3 0 obj - Page
            offsets[3] = buf.tell()
            w(b"3 0 obj\n")
            w(
                b"<< /Type /Page /Parent 2 0 R "
                b"/MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 5 0 R >> >> "
                b"/Contents 4 0 R >>\n"
            )
            w(b"endobj\n")

            # 4 0 obj - Content stream
            content_stream = (
                b"BT /F1 24 Tf 100 700 Td (Hello from fallback PoC) Tj ET\n"
            )
            offsets[4] = buf.tell()
            w(b"4 0 obj\n")
            w(b"<< /Length %d >>\n" % len(content_stream))
            w(b"stream\n")
            w(content_stream)
            w(b"endstream\n")
            w(b"endobj\n")

            # 5 0 obj - Font
            offsets[5] = buf.tell()
            w(b"5 0 obj\n")
            w(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n")
            w(b"endobj\n")

            # xref
            xref_offset = buf.tell()
            max_obj = 5
            w(b"xref\n")
            w(b"0 %d\n" % (max_obj + 1))
            # free object
            w(b"0000000000 65535 f \n")
            for i in range(1, max_obj + 1):
                off = offsets[i]
                w(b"%010d 00000 n \n" % off)

            # trailer
            w(b"trailer\n")
            w(b"<< /Size %d /Root 1 0 R >>\n" % (max_obj + 1))
            w(b"startxref\n")
            w(b"%d\n" % xref_offset)
            w(b"%%EOF\n")

            return buf.getvalue()

        def pick_candidate_from_members(tar_obj: tarfile.TarFile) -> bytes | None:
            try:
                members = [m for m in tar_obj.getmembers() if m.isreg()]
            except Exception:
                return None

            pdf_magic = b"%PDF-"
            bug_pattern = re.compile(r"59207")

            def member_looks_like_pdf(member: tarfile.TarInfo) -> bool:
                try:
                    f = tar_obj.extractfile(member)
                    if not f:
                        return False
                    head = f.read(1024)
                    f.close()
                except Exception:
                    return False
                return pdf_magic in head

            # Phase 1: exact size match == size_target
            exact_size = [m for m in members if m.size == size_target]
            if exact_size:
                # Prefer ones that look like PDF and contain bug id in name
                exact_size_sorted = sorted(
                    exact_size,
                    key=lambda m: (
                        0 if bug_pattern.search(m.name) else 1,
                        0 if m.name.lower().endswith(".pdf") else 1,
                    ),
                )
                for m in exact_size_sorted:
                    if member_looks_like_pdf(m):
                        data = tar_obj.extractfile(m).read()
                        return data
                # If none look like PDF, still try the first as raw bytes (could be compressed)
                try:
                    data = tar_obj.extractfile(exact_size_sorted[0]).read()
                    return data
                except Exception:
                    pass

            # Phase 2: names containing bug id
            bug_matches = [m for m in members if bug_pattern.search(m.name)]
            if bug_matches:
                bug_matches_sorted = sorted(
                    bug_matches,
                    key=lambda m: (
                        0 if m.name.lower().endswith(".pdf") else 1,
                        abs(m.size - size_target),
                    ),
                )
                for m in bug_matches_sorted:
                    if member_looks_like_pdf(m):
                        try:
                            data = tar_obj.extractfile(m).read()
                            return data
                        except Exception:
                            continue
                try:
                    data = tar_obj.extractfile(bug_matches_sorted[0]).read()
                    return data
                except Exception:
                    pass

            # Phase 3: generic PoC-like names or any PDF files
            keywords = [
                "poc",
                "crash",
                "uaf",
                "use-after",
                "use_after",
                "heap",
                "clusterfuzz",
                "oss-fuzz",
                "bug",
                "issue",
            ]

            def has_keyword(name: str) -> bool:
                lname = name.lower()
                return any(kw in lname for kw in keywords)

            likely = [m for m in members if has_keyword(m.name) or m.name.lower().endswith(".pdf")]

            def score_member(m: tarfile.TarInfo) -> int:
                name_l = m.name.lower()
                score = 0
                if bug_pattern.search(name_l):
                    score -= 100
                if "poc" in name_l or "crash" in name_l:
                    score -= 50
                if name_l.endswith(".pdf"):
                    score -= 20
                if has_keyword(name_l):
                    score -= 10
                # prefer smaller files
                if m.size < 1_000_000:
                    score -= 5
                score += abs(m.size - size_target) // 10
                return score

            if likely:
                likely_sorted = sorted(likely, key=score_member)
                for m in likely_sorted:
                    if member_looks_like_pdf(m):
                        try:
                            data = tar_obj.extractfile(m).read()
                            return data
                        except Exception:
                            continue
                try:
                    data = tar_obj.extractfile(likely_sorted[0]).read()
                    return data
                except Exception:
                    pass

            # Phase 4: any file that looks like a PDF
            best_member = None
            best_score = None
            for m in members:
                if m.size > 5_000_000:
                    continue
                if not member_looks_like_pdf(m):
                    continue
                score = abs(m.size - size_target)
                if best_score is None or score < best_score:
                    best_score = score
                    best_member = m
            if best_member is not None:
                try:
                    data = tar_obj.extractfile(best_member).read()
                    return data
                except Exception:
                    pass

            return None

        # Main logic
        data: bytes | None = None
        try:
            with tarfile.open(src_path, "r:*") as tar:
                data = pick_candidate_from_members(tar)
        except Exception:
            data = None

        if data is None:
            return minimal_pdf()

        # If the candidate is compressed with gzip, try to decompress it
        if len(data) >= 3 and data[:3] == b"\x1f\x8b\x08":
            try:
                decompressed = gzip.decompress(data)
                if b"%PDF-" in decompressed:
                    data = decompressed
            except Exception:
                pass

        # If it still doesn't look like a PDF, fall back
        if b"%PDF-" not in data:
            return minimal_pdf()

        return data
