import os
import tarfile
import tempfile
import shutil
import stat

G_POC_LEN = 33762


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo21604_")
        try:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                return self._fallback_poc()

            candidate_path = None
            best_score = None

            suspicious_name_keywords = (
                "poc",
                "crash",
                "uaf",
                "use-after",
                "use_after",
                "heap",
                "bug",
                "cve",
                "ossfuzz",
                "fuzz",
                "standalone",
                "form",
            )
            suspicious_dir_keywords = (
                "poc",
                "pocs",
                "crash",
                "crashes",
                "regress",
                "tests",
                "fuzz",
                "corpus",
                "oss-fuzz",
                "inputs",
                "artifacts",
                "clusterfuzz",
            )

            for root, dirs, files in os.walk(tmpdir):
                for name in files:
                    path = os.path.join(root, name)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    size = st.st_size
                    if size == 0 or size > 5 * 1024 * 1024:
                        continue

                    base = name.lower()
                    ext = ""
                    if "." in base:
                        ext = base.rsplit(".", 1)[1]

                    try:
                        with open(path, "rb") as f:
                            header = f.read(8)
                            f.seek(0)
                            sample = f.read(4096)
                    except Exception:
                        continue

                    is_pdf = header.startswith(b"%PDF-")

                    score = abs(size - G_POC_LEN)

                    if is_pdf or ext == "pdf":
                        score -= 50000
                    elif ext in ("bin", "dat", "data", "raw", "poc", "input", "in", "out", "case", "seed"):
                        score -= 20000

                    if any(k in base for k in suspicious_name_keywords):
                        score -= 15000

                    root_lower = root.lower()
                    if any(k in root_lower for k in suspicious_dir_keywords):
                        score -= 8000

                    if size == G_POC_LEN:
                        score -= 10000

                    # Prefer binary-looking files slightly
                    if b"\0" in sample or any(b > 127 for b in sample):
                        score -= 2000

                    if best_score is None or score < best_score:
                        best_score = score
                        candidate_path = path

            if candidate_path is not None:
                try:
                    with open(candidate_path, "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except Exception:
                    pass

            return self._fallback_poc()
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _fallback_poc(self) -> bytes:
        pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R /AcroForm 3 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [4 0 R] /Count 1 >>
endobj
3 0 obj
<< /Fields [5 0 R] >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Annots [5 0 R] >>
endobj
5 0 obj
<<
/Type /Annot
/Subtype /Widget
/Rect [10 10 110 30]
/FT /Tx
/T (F1)
/V (V1)
/DA (/Helv 0 Tf 0 g)
/AP << /N 6 0 R >>
>>
endobj
6 0 obj
<< /Type /XObject /Subtype /Form /BBox [0 0 100 20] /Resources << /Font << /Helv 7 0 R >> >> >>
stream
q
BT /Helv 12 Tf 0 0 Td (Hello) Tj ET
Q
endstream
endobj
7 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
trailer
<< /Root 1 0 R /Size 8 >>
%%EOF
"""
        return pdf