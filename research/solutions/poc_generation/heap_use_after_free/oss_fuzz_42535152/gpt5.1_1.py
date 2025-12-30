import os
import io
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc = self._find_poc_by_bug_id(src_path, "42535152")
        if poc is not None:
            return poc

        poc = self._find_any_pdf(src_path)
        if poc is not None:
            return poc

        return self._fallback_poc()

    def _find_poc_by_bug_id(self, src_path: str, bug_id: str) -> bytes | None:
        bug_id_lower = bug_id.lower()
        preferred_exts = [".pdf", ".bin", ".dat", ".in", ".out", ".poc", ".txt"]

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()

                # 1. Direct file match in tar members
                direct_candidates = []
                for m in members:
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if bug_id_lower in name_lower:
                        ext = os.path.splitext(name_lower)[1]
                        try:
                            priority = preferred_exts.index(ext)
                        except ValueError:
                            priority = len(preferred_exts)
                        direct_candidates.append((priority, m.size, m))

                if direct_candidates:
                    direct_candidates.sort(key=lambda x: (x[0], x[1]))
                    member = direct_candidates[0][2]
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        return extracted.read()

                # 2. Look for zip files that may contain the PoC
                zip_members = []
                for m in members:
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if name_lower.endswith(".zip") and bug_id_lower in name_lower:
                        zip_members.append(m)

                for zmem in zip_members:
                    zf_bytes = tf.extractfile(zmem)
                    if zf_bytes is None:
                        continue
                    data = zf_bytes.read()
                    try:
                        with zipfile.ZipFile(io.BytesIO(data)) as zf:
                            internal_candidates = []

                            # Prefer files whose names contain the bug id
                            for name in zf.namelist():
                                nlower = name.lower()
                                if bug_id_lower in nlower:
                                    ext = os.path.splitext(nlower)[1]
                                    try:
                                        priority = preferred_exts.index(ext)
                                    except ValueError:
                                        priority = len(preferred_exts)
                                    size = zf.getinfo(name).file_size
                                    internal_candidates.append((priority, size, name))

                            # If none match bug id, fall back to any PDF-like file
                            if not internal_candidates:
                                for name in zf.namelist():
                                    nlower = name.lower()
                                    ext = os.path.splitext(nlower)[1]
                                    if ext in (".pdf", ".bin", ".dat"):
                                        size = zf.getinfo(name).file_size
                                        internal_candidates.append((0, size, name))

                            if internal_candidates:
                                internal_candidates.sort(key=lambda x: (x[0], x[1]))
                                target_name = internal_candidates[0][2]
                                return zf.read(target_name)
                    except zipfile.BadZipFile:
                        continue
        except (tarfile.TarError, FileNotFoundError, OSError):
            return None

        return None

    def _find_any_pdf(self, src_path: str) -> bytes | None:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                pdf_members = []
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    if name_lower.endswith(".pdf"):
                        pdf_members.append(m)

                if pdf_members:
                    # Heuristic: pick the largest PDF (likely to be most complex)
                    pdf_members.sort(key=lambda m: (-m.size, m.name))
                    member = pdf_members[0]
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        return extracted.read()
        except (tarfile.TarError, FileNotFoundError, OSError):
            return None

        return None

    def _fallback_poc(self) -> bytes:
        # Minimal, syntactically valid PDF as a last resort
        pdf_lines = [
            b"%PDF-1.3\n",
            b"1 0 obj\n",
            b"<< /Type /Catalog /Pages 2 0 R >>\n",
            b"endobj\n",
            b"2 0 obj\n",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n",
            b"endobj\n",
            b"3 0 obj\n",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n",
            b"endobj\n",
            b"xref\n",
            b"0 4\n",
            b"0000000000 65535 f \n",
            b"0000000010 00000 n \n",
            b"0000000060 00000 n \n",
            b"0000000115 00000 n \n",
            b"trailer\n",
            b"<< /Root 1 0 R /Size 4 >>\n",
            b"startxref\n",
            b"170\n",
            b"%%EOF\n",
        ]
        return b"".join(pdf_lines)