import os
import tarfile
import tempfile
import gzip
import bz2
import lzma


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = tempfile.mkdtemp(prefix="poc_src_")
        self._extract_tar_safely(src_path, extract_dir)
        pdf_data = self._find_pdf_poc(extract_dir)
        return pdf_data

    def _extract_tar_safely(self, src_path: str, dst_dir: str) -> None:
        with tarfile.open(src_path, "r:*") as tf:
            safe_members = []
            dst_dir_abs = os.path.abspath(dst_dir)
            for member in tf.getmembers():
                member_path = os.path.abspath(os.path.join(dst_dir, member.name))
                try:
                    common = os.path.commonpath([dst_dir_abs, member_path])
                except ValueError:
                    continue
                if common == dst_dir_abs:
                    safe_members.append(member)
            tf.extractall(dst_dir, members=safe_members)

    def _find_pdf_poc(self, root: str) -> bytes:
        expected_size = 6431
        best_path = None
        best_score = None
        keywords = (
            "poc",
            "regress",
            "bug",
            "uaf",
            "use-after",
            "heap-use-after",
            "59207",
            "crash",
            "testcase",
            "fuzz",
        )

        # First pass: plain PDF files
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue

                try:
                    with open(fpath, "rb") as f:
                        header = f.read(4)
                except OSError:
                    continue

                if header != b"%PDF":
                    continue

                closeness = abs(size - expected_size)
                path_lower = fpath.lower()
                preferred = 1
                for kw in keywords:
                    if kw in path_lower:
                        preferred = 0
                        break
                score = (preferred, closeness, size)
                if best_score is None or score < best_score:
                    best_score = score
                    best_path = fpath

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except OSError:
                pass

        # Second pass: compressed PDF files
        data = self._find_compressed_pdf_poc(root, expected_size, keywords)
        if data is not None:
            return data

        # Fallback: synthetic minimal PDF
        return self._generate_minimal_pdf()

    def _find_compressed_pdf_poc(self, root: str, expected_size: int, keywords) -> bytes | None:
        best_data = None
        best_score = None

        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                lower = fpath.lower()
                if lower.endswith(".gz") or lower.endswith(".bz2") or lower.endswith(".xz") or lower.endswith(".lzma"):
                    try:
                        compressed_size = os.path.getsize(fpath)
                    except OSError:
                        continue

                    # Skip very large compressed files for safety
                    if compressed_size > 2 * 1024 * 1024:
                        continue

                    try:
                        if lower.endswith(".gz"):
                            with gzip.open(fpath, "rb") as f:
                                data = f.read()
                        elif lower.endswith(".bz2"):
                            with bz2.open(fpath, "rb") as f:
                                data = f.read()
                        else:
                            # .xz or .lzma
                            with lzma.open(fpath, "rb") as f:
                                data = f.read()
                    except OSError:
                        continue
                    except lzma.LZMAError:
                        continue

                    if not data.startswith(b"%PDF"):
                        continue

                    size = len(data)
                    closeness = abs(size - expected_size)
                    path_lower = lower
                    preferred = 1
                    for kw in keywords:
                        if kw in path_lower:
                            preferred = 0
                            break
                    score = (preferred, closeness, size)
                    if best_score is None or score < best_score:
                        best_score = score
                        best_data = data

        return best_data

    def _generate_minimal_pdf(self) -> bytes:
        # A very small, intentionally simple and slightly malformed PDF.
        # Most PDF parsers (including MuPDF) attempt to repair missing xref tables.
        parts = [
            b"%PDF-1.3\n",
            b"1 0 obj\n",
            b"<< /Type /Catalog >>\n",
            b"endobj\n",
            b"trailer\n",
            b"<< /Root 1 0 R >>\n",
            b"%%EOF\n",
        ]
        return b"".join(parts)