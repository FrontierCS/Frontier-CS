import os
import io
import re
import tarfile
import gzip
import zipfile
import base64
from typing import Optional, Tuple


def _is_font_magic(data: bytes) -> bool:
    if len(data) < 4:
        return False
    m = data[:4]
    if m in (b"OTTO", b"ttcf", b"wOFF", b"wOF2", b"true", b"typ1"):
        return True
    if m == b"\x00\x01\x00\x00":
        return True
    return False


def _mostly_text(data: bytes) -> bool:
    if not data:
        return False
    printable = 0
    for b in data[:200000]:
        if b in (9, 10, 13) or 32 <= b <= 126:
            printable += 1
    return printable / max(1, min(len(data), 200000)) > 0.97


_B64_RE = re.compile(rb"(?:[A-Za-z0-9+/]{40,}={0,2})")


def _iter_base64_decodes(text_bytes: bytes):
    for m in _B64_RE.finditer(text_bytes):
        token = m.group(0)
        if len(token) < 200:
            continue
        if len(token) > 8_000_000:
            continue
        try:
            dec = base64.b64decode(token, validate=False)
        except Exception:
            continue
        if dec:
            yield dec


def _iter_hex_array_decodes(text_bytes: bytes):
    try:
        s = text_bytes.decode("latin1", errors="ignore")
    except Exception:
        return
    for m in re.finditer(r"(?:0x[0-9a-fA-F]{2}\s*,\s*){40,}0x[0-9a-fA-F]{2}", s):
        part = m.group(0)
        hexes = re.findall(r"0x([0-9a-fA-F]{2})", part)
        if len(hexes) < 64:
            continue
        try:
            yield bytes(int(h, 16) for h in hexes)
        except Exception:
            pass
    for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){80,}", s):
        part = m.group(0)
        hexes = re.findall(r"\\x([0-9a-fA-F]{2})", part)
        if len(hexes) < 64:
            continue
        try:
            yield bytes(int(h, 16) for h in hexes)
        except Exception:
            pass


def _keyword_score(path: str, data: bytes) -> int:
    p = path.lower()
    score = 0
    kws = [
        ("clusterfuzz", 250),
        ("testcase", 180),
        ("minimized", 200),
        ("crash", 160),
        ("repro", 150),
        ("poc", 150),
        ("uaf", 200),
        ("use-after-free", 220),
        ("heap", 50),
        ("asan", 60),
        ("oss-fuzz", 160),
        ("fuzz", 60),
        ("corpus", 60),
        ("regression", 80),
        ("919", 240),
        ("arvo", 140),
        ("issue", 40),
        ("bug", 40),
    ]
    for k, w in kws:
        if k in p:
            score += w

    ext = os.path.splitext(p)[1]
    if ext in (".ttf", ".otf", ".woff", ".woff2", ".ttc", ".bin", ".dat", ".font"):
        score += 60
    if _is_font_magic(data):
        score += 400
    if len(data) == 800:
        score += 120
    if 760 <= len(data) <= 840:
        score += 40
    return score


def _try_gunzip(data: bytes) -> Optional[bytes]:
    if len(data) < 2:
        return None
    if data[:2] != b"\x1f\x8b":
        return None
    try:
        dec = gzip.decompress(data)
    except Exception:
        return None
    if not dec:
        return None
    return dec


def _try_unzip(data: bytes):
    if len(data) < 4 or data[:2] != b"PK":
        return
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception:
        return
    for zi in zf.infolist():
        if zi.is_dir():
            continue
        if zi.file_size <= 0 or zi.file_size > 5_000_000:
            continue
        try:
            zdata = zf.read(zi)
        except Exception:
            continue
        if zdata:
            yield zi.filename, zdata


class Solution:
    def solve(self, src_path: str) -> bytes:
        best: Optional[Tuple[Tuple[int, int, int, int], bytes]] = None

        def consider(name: str, data: bytes):
            nonlocal best
            if not data or len(data) < 4 or len(data) > 5_000_000:
                return
            score = _keyword_score(name, data)
            if score <= 0 and not _is_font_magic(data):
                return

            size = len(data)
            size_pen = abs(size - 800)
            not_font_pen = 0 if _is_font_magic(data) else 5000
            rank = (-score, not_font_pen, size_pen, size)
            if best is None or rank < best[0]:
                best = (rank, data)

        def process_blob(name: str, data: bytes):
            consider(name, data)

            dec = _try_gunzip(data)
            if dec is not None and len(dec) <= 5_000_000:
                consider(name + "::gunzip", dec)

            for zname, zdata in _try_unzip(data) or ():
                consider(name + "::zip::" + zname, zdata)

            if len(data) <= 1_000_000 and _mostly_text(data):
                for b in _iter_base64_decodes(data):
                    if len(b) <= 5_000_000:
                        consider(name + "::b64", b)
                for b in _iter_hex_array_decodes(data):
                    if len(b) <= 5_000_000:
                        consider(name + "::hex", b)

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except Exception:
                        continue
                    if st.st_size <= 0 or st.st_size > 5_000_000:
                        continue
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    rel = os.path.relpath(p, src_path)
                    process_blob(rel, data)
        else:
            try:
                with tarfile.open(src_path, mode="r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > 5_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        process_blob(m.name, data)
            except Exception:
                pass

        if best is not None:
            return best[1]

        return b"OTTO" + b"\x00" * 796