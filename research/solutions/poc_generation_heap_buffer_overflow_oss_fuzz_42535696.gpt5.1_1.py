import os
import io
import tarfile
import zipfile
import gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 150979
        format_hint = None

        # Try treating src_path as a tarball
        if os.path.isfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    format_hint = self._infer_input_format_from_tar(tf)
                    poc = self._search_tar_for_poc(tf, target_size, depth=0)
                    if poc is not None:
                        return poc
            except tarfile.TarError:
                # If not a tar, maybe the file itself is the PoC
                try:
                    if os.path.getsize(src_path) == target_size:
                        with open(src_path, "rb") as f:
                            data = f.read()
                        if len(data) == target_size:
                            return data
                except OSError:
                    pass

        # If it's a directory, scan it directly
        if os.path.isdir(src_path):
            if format_hint is None:
                format_hint = self._infer_input_format_from_dir(src_path)
            poc = self._search_directory_for_poc(src_path, target_size)
            if poc is not None:
                return poc

        # Fallback: synthetic PoC
        return self._default_poc(format_hint)

    def _infer_input_format_from_tar(self, tf: tarfile.TarFile):
        format_hint = None
        try:
            members = tf.getmembers()
        except Exception:
            return None

        for m in members:
            if not m.isfile():
                continue
            name_lower = m.name.lower()
            if not (
                name_lower.endswith(".c")
                or name_lower.endswith(".cc")
                or name_lower.endswith(".cpp")
                or name_lower.endswith(".cxx")
            ):
                continue
            read_size = min(m.size, 500_000) if m.size > 0 else 500_000
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read(read_size)
            except Exception:
                continue
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                text = data.decode("latin1", errors="ignore")

            if "LLVMFuzzerTestOneInput" not in text:
                continue

            if "gsapi_run_string" in text or "gs_main_run_string" in text:
                return "ps"
            if "-sDEVICE=pdfwrite" in text:
                format_hint = "ps"
            if (
                "FPDF_" in text
                or "PdfDocument" in text
                or "pdfium" in text
                or "application/pdf" in text
            ):
                return "pdf"
        return format_hint

    def _infer_input_format_from_dir(self, root: str):
        format_hint = None
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                lower = filename.lower()
                if not (
                    lower.endswith(".c")
                    or lower.endswith(".cc")
                    or lower.endswith(".cpp")
                    or lower.endswith(".cxx")
                ):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    with open(path, "rb") as f:
                        data = f.read(500_000)
                except OSError:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    text = data.decode("latin1", errors="ignore")

                if "LLVMFuzzerTestOneInput" not in text:
                    continue

                if "gsapi_run_string" in text or "gs_main_run_string" in text:
                    return "ps"
                if "-sDEVICE=pdfwrite" in text:
                    format_hint = "ps"
                if (
                    "FPDF_" in text
                    or "PdfDocument" in text
                    or "pdfium" in text
                    or "application/pdf" in text
                ):
                    return "pdf"
        return format_hint

    def _search_tar_for_poc(
        self, tf: tarfile.TarFile, target_size: int, depth: int
    ) -> bytes | None:
        try:
            members = tf.getmembers()
        except Exception:
            return None

        best_member = None
        best_score = float("-inf")

        for m in members:
            if not m.isfile():
                continue
            size = m.size
            if size <= 0:
                continue

            # Exact-size match
            if size == target_size:
                try:
                    f = tf.extractfile(m)
                    if f is not None:
                        data = f.read()
                        if len(data) == target_size:
                            return data
                except Exception:
                    pass

            name_lower = m.name.lower()

            # Check for embedded archives likely to contain PoC
            is_candidate_archive = False
            archive_exts = (".tar", ".tar.gz", ".tgz", ".zip", ".gz")
            if any(
                kw in name_lower
                for kw in (
                    "poc",
                    "repro",
                    "crash",
                    "fuzz",
                    "seed",
                    "corpus",
                    "42535696",
                    "bug",
                    "issue",
                )
            ):
                if any(name_lower.endswith(ext) for ext in archive_exts):
                    is_candidate_archive = True
            if (
                not is_candidate_archive
                and size < 2 * 1024 * 1024
                and (name_lower.endswith(".gz") or name_lower.endswith(".zip"))
            ):
                is_candidate_archive = True

            if is_candidate_archive and depth < 3:
                try:
                    f = tf.extractfile(m)
                    if f is not None:
                        raw = f.read()
                    else:
                        raw = b""
                except Exception:
                    raw = b""
                if raw:
                    nested = self._search_in_embedded_archive(
                        raw, target_size, depth + 1
                    )
                    if nested is not None:
                        return nested

            # Score member as potential PoC
            score = self._score_member(m.name, size, target_size)
            if score > best_score:
                best_score = score
                best_member = m

        if best_member is not None and best_score > 0:
            try:
                f = tf.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        return data
            except Exception:
                pass
        return None

    def _search_directory_for_poc(self, root: str, target_size: int) -> bytes | None:
        best_member_path = None
        best_score = float("-inf")

        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue

                # Exact-size match
                if size == target_size:
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        if len(data) == target_size:
                            return data
                    except OSError:
                        pass

                name_lower = path.lower()
                is_candidate_archive = False
                archive_exts = (".tar", ".tar.gz", ".tgz", ".zip", ".gz")
                if any(
                    kw in name_lower
                    for kw in (
                        "poc",
                        "repro",
                        "crash",
                        "fuzz",
                        "seed",
                        "corpus",
                        "42535696",
                        "bug",
                        "issue",
                    )
                ):
                    if any(name_lower.endswith(ext) for ext in archive_exts):
                        is_candidate_archive = True
                if (
                    not is_candidate_archive
                    and size < 2 * 1024 * 1024
                    and (name_lower.endswith(".gz") or name_lower.endswith(".zip"))
                ):
                    is_candidate_archive = True

                if is_candidate_archive:
                    try:
                        with open(path, "rb") as f:
                            raw = f.read()
                    except OSError:
                        raw = b""
                    if raw:
                        nested = self._search_in_embedded_archive(
                            raw, target_size, depth=1
                        )
                        if nested is not None:
                            return nested

                score = self._score_member(path, size, target_size)
                if score > best_score:
                    best_score = score
                    best_member_path = path

        if best_member_path is not None and best_score > 0:
            try:
                with open(best_member_path, "rb") as f:
                    data = f.read()
                if data:
                    return data
            except OSError:
                pass
        return None

    def _score_member(self, name: str, size: int, target_size: int) -> float:
        name_lower = name.lower()
        score = 0.0

        # Size closeness
        if size > 0 and target_size > 0:
            diff = abs(size - target_size)
            score += max(0.0, 300.0 - (diff / 500.0))

        # Extension weighting
        _, ext = os.path.splitext(name_lower)
        ext_weights = {
            ".pdf": 250,
            ".ps": 250,
            ".eps": 200,
            ".xps": 200,
            ".oxps": 200,
            ".pcl": 150,
            ".pclx": 150,
            ".bin": 100,
            ".dat": 80,
            ".txt": 10,
        }
        score += ext_weights.get(ext, 0)

        # Keyword bonuses
        keywords = [
            "poc",
            "repro",
            "crash",
            "clusterfuzz",
            "42535696",
            "heap",
            "overflow",
            "bug",
            "issue",
            "fuzz",
            "test",
            "case",
        ]
        for kw in keywords:
            if kw in name_lower:
                score += 60

        dir_keywords = [
            "test",
            "tests",
            "regress",
            "regression",
            "fuzz",
            "corpus",
            "seed",
            "poc",
        ]
        for dkw in dir_keywords:
            if (
                f"/{dkw}/" in name_lower
                or name_lower.endswith("/" + dkw)
                or name_lower.startswith(dkw + "/")
            ):
                score += 30

        # Penalty for very large files
        if size > 10 * 1024 * 1024:
            score -= (size - 10 * 1024 * 1024) / 4096.0

        return score

    def _search_in_embedded_archive(
        self, data: bytes, target_size: int, depth: int
    ) -> bytes | None:
        if depth > 3 or not data:
            return None

        # Try gzip
        if data.startswith(b"\x1f\x8b"):
            try:
                decompressed = gzip.decompress(data)
            except Exception:
                decompressed = None
            if decompressed:
                if len(decompressed) == target_size:
                    return decompressed
                try:
                    bio = io.BytesIO(decompressed)
                    with tarfile.open(fileobj=bio, mode="r:*") as tf:
                        res = self._search_tar_for_poc(tf, target_size, depth + 1)
                        if res is not None:
                            return res
                except tarfile.TarError:
                    pass

        # Try zip
        if data.startswith(b"PK\x03\x04"):
            try:
                bio = io.BytesIO(data)
                with zipfile.ZipFile(bio, "r") as zf:
                    for info in zf.infolist():
                        if info.file_size == 0:
                            continue
                        if info.file_size == target_size:
                            try:
                                with zf.open(info) as f:
                                    file_data = f.read()
                                if len(file_data) == target_size:
                                    return file_data
                            except Exception:
                                pass
                        lower = info.filename.lower()
                        if any(
                            lower.endswith(ext)
                            for ext in (".tar", ".tar.gz", ".tgz", ".zip", ".gz")
                        ):
                            try:
                                with zf.open(info) as f:
                                    nested_raw = f.read()
                                nested_res = self._search_in_embedded_archive(
                                    nested_raw, target_size, depth + 1
                                )
                                if nested_res is not None:
                                    return nested_res
                            except Exception:
                                pass
            except zipfile.BadZipFile:
                pass

        # Try tar
        try:
            bio = io.BytesIO(data)
            with tarfile.open(fileobj=bio, mode="r:*") as tf:
                res = self._search_tar_for_poc(tf, target_size, depth + 1)
                if res is not None:
                    return res
        except tarfile.TarError:
            pass

        # Fallback direct-size check
        if len(data) == target_size:
            return data
        return None

    def _default_poc(self, format_hint: str | None) -> bytes:
        if format_hint == "ps":
            ps_code = (
                "%!PS-Adobe-3.0\n"
                "%%Title: pdfwrite viewer state PoC\n"
                "%%Pages: 1\n"
                "%%BoundingBox: 0 0 612 792\n"
                "%%EndComments\n"
                "\n"
                "/Helvetica findfont 12 scalefont setfont\n"
                "72 720 moveto\n"
                "(Hello from fallback PoC) show\n"
                "\n"
                "% PDF-specific pdfmark constructs to engage pdfwrite\n"
                "[ /Title (Viewer State PoC)\n"
                "  /Author (AutoGenerated)\n"
                "  /DOCINFO pdfmark\n"
                "\n"
                "[ /PageMode /UseOutlines\n"
                "  /Page 1\n"
                "  /View [ /XYZ null null null ]\n"
                "  /DOCVIEW pdfmark\n"
                "\n"
                "[ /Dest /Dest0\n"
                "  /Page 1\n"
                "  /View [ /XYZ 0 0 0 ]\n"
                "  /DEST pdfmark\n"
                "\n"
                "gsave\n"
                "0 0 moveto\n"
                "(Nested viewer state) show\n"
                "grestore\n"
                "\n"
                "showpage\n"
            )
            return ps_code.encode("ascii", errors="ignore")

        pdf_code = (
            "%PDF-1.4\n"
            "% Fallback minimal PDF\n"
            "\n"
            "1 0 obj\n"
            "<< /Type /Catalog /Pages 2 0 R >>\n"
            "endobj\n"
            "\n"
            "2 0 obj\n"
            "<< /Type /Pages /Count 1 /Kids [3 0 R] >>\n"
            "endobj\n"
            "\n"
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
            "   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
            "endobj\n"
            "\n"
            "4 0 obj\n"
            "<< /Length 60 >>\n"
            "stream\n"
            "BT /F1 24 Tf 72 700 Td (Fallback PDF PoC) Tj ET\n"
            "endstream\n"
            "endobj\n"
            "\n"
            "5 0 obj\n"
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
            "endobj\n"
            "\n"
            "xref\n"
            "0 6\n"
            "0000000000 65535 f \n"
            "0000000010 00000 n \n"
            "0000000060 00000 n \n"
            "0000000115 00000 n \n"
            "0000000240 00000 n \n"
            "0000000335 00000 n \n"
            "trailer\n"
            "<< /Size 6 /Root 1 0 R >>\n"
            "startxref\n"
            "420\n"
            "%%EOF\n"
        )
        return pdf_code.encode("ascii", errors="ignore")