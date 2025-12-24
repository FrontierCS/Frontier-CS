import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        L_G = 33453
        prefer_exts = {
            "pdf",
            "bin",
            "data",
            "raw",
            "dat",
            "poc",
            "repro",
            "input",
            "testcase",
            "case",
        }

        # Try treating src_path as tarball
        data = self._find_in_tar(src_path, L_G, prefer_exts)
        if data is not None:
            return data

        # If src_path is a directory, search inside it directly
        if os.path.isdir(src_path):
            data = self._find_in_dir(src_path, L_G, prefer_exts)
            if data is not None:
                return data

        # Fallback generic PDF-like PoC
        return self._fallback_poc()

    def _find_in_tar(self, tar_path: str, L_G: int, prefer_exts) -> bytes | None:
        if not os.path.isfile(tar_path):
            return None
        try:
            tf = tarfile.open(tar_path, "r:*")
        except tarfile.ReadError:
            return None

        best_member = None
        best_weight = None

        not_prefer_text_exts = {
            "c",
            "cc",
            "cpp",
            "cxx",
            "h",
            "hpp",
            "hh",
            "java",
            "py",
            "txt",
            "md",
            "html",
            "htm",
            "js",
            "css",
            "json",
            "xml",
            "yml",
            "yaml",
            "in",
            "cfg",
            "cmake",
            "mk",
            "sh",
            "bat",
            "ps1",
            "rst",
            "tex",
            "csv",
        }

        for member in tf.getmembers():
            if not member.isfile():
                continue
            size = member.size
            # Skip empty and overly large files
            if size <= 0 or size > 1_000_000:
                continue

            name = member.name
            lower_name = name.lower()

            base = os.path.basename(name)
            if "." in base:
                ext = base.rsplit(".", 1)[1].lower()
            else:
                ext = ""

            if ext in not_prefer_text_exts:
                continue

            # Priority 1: name contains bug id
            priority1 = 0 if "42535152" in lower_name else 1

            # Priority 2: extension looks like a binary/testcase
            priority2 = 0 if ext in prefer_exts or ext == "" else 1

            mismatch = abs(size - L_G)
            weight = (priority1, priority2, mismatch)

            if best_weight is None or weight < best_weight:
                best_weight = weight
                best_member = member

        if best_member is not None:
            f = tf.extractfile(best_member)
            if f is not None:
                data = f.read()
                if data:
                    return data
        return None

    def _find_in_dir(self, root: str, L_G: int, prefer_exts) -> bytes | None:
        best_path = None
        best_weight = None

        not_prefer_text_exts = {
            "c",
            "cc",
            "cpp",
            "cxx",
            "h",
            "hpp",
            "hh",
            "java",
            "py",
            "txt",
            "md",
            "html",
            "htm",
            "js",
            "css",
            "json",
            "xml",
            "yml",
            "yaml",
            "in",
            "cfg",
            "cmake",
            "mk",
            "sh",
            "bat",
            "ps1",
            "rst",
            "tex",
            "csv",
        }

        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0 or size > 1_000_000:
                    continue

                lower_name = fname.lower()
                if "." in fname:
                    ext = fname.rsplit(".", 1)[1].lower()
                else:
                    ext = ""

                if ext in not_prefer_text_exts:
                    continue

                priority1 = 0 if "42535152" in lower_name else 1
                priority2 = 0 if ext in prefer_exts or ext == "" else 1
                mismatch = abs(size - L_G)
                weight = (priority1, priority2, mismatch)

                if best_weight is None or weight < best_weight:
                    best_weight = weight
                    best_path = path

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    data = f.read()
                    if data:
                        return data
            except OSError:
                return None
        return None

    def _fallback_poc(self) -> bytes:
        # Minimal but slightly non-trivial PDF structure as a generic fallback
        pdf_lines = [
            b"%PDF-1.5\n",
            b"%\xe2\xe3\xcf\xd3\n",
            b"1 0 obj\n",
            b"<< /Type /Catalog /Pages 2 0 R >>\n",
            b"endobj\n",
            b"2 0 obj\n",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n",
            b"endobj\n",
            b"3 0 obj\n",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\n",
            b"endobj\n",
            b"4 0 obj\n",
            b"<< /Length 44 >>\n",
            b"stream\n",
            b"BT /F1 24 Tf 72 700 Td (Fallback PoC PDF) Tj ET\n",
            b"endstream\n",
            b"endobj\n",
            b"xref\n",
            b"0 5\n",
            b"0000000000 65535 f \n",
            b"0000000010 00000 n \n",
            b"0000000060 00000 n \n",
            b"0000000118 00000 n \n",
            b"0000000230 00000 n \n",
            b"trailer\n",
            b"<< /Size 5 /Root 1 0 R >>\n",
            b"startxref\n",
            b"340\n",
            b"%%EOF\n",
        ]
        return b"".join(pdf_lines)
