import os
from typing import Dict, List, Tuple


class _PDFBuilder:
    def __init__(self) -> None:
        self.buf = bytearray()

    def tell(self) -> int:
        return len(self.buf)

    def write(self, data: bytes) -> None:
        self.buf.extend(data)

    def add_obj(self, objnum: int, body: bytes) -> int:
        off = self.tell()
        if not body.endswith(b"\n"):
            body += b"\n"
        self.write(f"{objnum} 0 obj\n".encode("ascii"))
        self.write(body)
        self.write(b"endobj\n")
        return off

    def add_stream_obj(self, objnum: int, dict_entries: str, stream_data: bytes) -> int:
        off = self.tell()
        if not stream_data.endswith(b"\n"):
            stream_data += b"\n"
        length = len(stream_data)
        d = f"<< {dict_entries} /Length {length} >>\n".encode("ascii")
        self.write(f"{objnum} 0 obj\n".encode("ascii"))
        self.write(d)
        self.write(b"stream\n")
        self.write(stream_data)
        self.write(b"endstream\nendobj\n")
        return off


def _xref_entry(t: int, f2: int, f3: int) -> bytes:
    return bytes((t & 0xFF,)) + int(f2).to_bytes(4, "big", signed=False) + int(f3).to_bytes(2, "big", signed=False)


def _xref_stream_data(index_ranges: List[Tuple[int, int]], entry_map: Dict[int, Tuple[int, int, int]]) -> bytes:
    out = bytearray()
    for start, count in index_ranges:
        for obj in range(start, start + count):
            if obj in entry_map:
                t, f2, f3 = entry_map[obj]
            else:
                if obj == 0:
                    t, f2, f3 = (0, 0, 65535)
                else:
                    t, f2, f3 = (0, 0, 0)
            out.extend(_xref_entry(t, f2, f3))
    return bytes(out)


def _fmt_index(index_ranges: List[Tuple[int, int]]) -> str:
    parts: List[str] = []
    for a, b in index_ranges:
        parts.append(str(a))
        parts.append(str(b))
    return "[ " + " ".join(parts) + " ]"


class Solution:
    def solve(self, src_path: str) -> bytes:
        b = _PDFBuilder()
        b.write(b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n")

        off_1 = b.add_obj(1, b"<< /Type /Catalog /Pages 2 0 R /OpenAction 5 0 R >>")
        off_2 = b.add_obj(2, b"<< /Type /Pages /Count 1 /Kids [ 3 0 R ] >>")
        off_3 = b.add_obj(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [ 0 0 200 200 ] /Resources << /ExtGState << /GS1 6 0 R >> >> /Contents 4 0 R >>",
        )
        off_4 = b.add_stream_obj(4, "", b"q\nQ\n")

        obj5_in_objstm = b"<< /S /GoTo /D [ 3 0 R /Fit ] /Old true >>"
        obj6_in_objstm = b"<< /Type /ExtGState /ca 1 /CA 1 >>"
        off2 = len(obj5_in_objstm) + 1
        header = f"5 0 6 {off2} ".encode("ascii")
        first = len(header)
        objstm_data = header + obj5_in_objstm + b"\n" + obj6_in_objstm + b"\n"
        off_10 = b.add_stream_obj(10, f"/Type /ObjStm /N 2 /First {first}", objstm_data)

        off_20 = b.tell()
        index1 = [(0, 21)]
        entry_map1: Dict[int, Tuple[int, int, int]] = {
            0: (0, 0, 65535),
            1: (1, off_1, 0),
            2: (1, off_2, 0),
            3: (1, off_3, 0),
            4: (1, off_4, 0),
            5: (2, 10, 0),
            6: (2, 10, 1),
            10: (1, off_10, 0),
            20: (1, off_20, 0),
        }
        xref1_data = _xref_stream_data(index1, entry_map1)
        dict1 = f"/Type /XRef /Size 21 /W [ 1 4 2 ] /Index {_fmt_index(index1)} /Root 1 0 R"
        b.add_stream_obj(20, dict1, xref1_data)

        b.write(b"startxref\n" + str(off_20).encode("ascii") + b"\n%%EOF\n")

        prev_off = off_20
        prev_xref_objnum = 20
        updates = 5
        for i in range(1, updates + 1):
            off_obj5 = b.add_obj(5, f"<< /S /GoTo /D [ 3 0 R /Fit ] /Upd {i} >>".encode("ascii"))
            xref_objnum = prev_xref_objnum + 1
            off_xref = b.tell()

            idx = [(0, 1), (5, 1), (xref_objnum, 1)]
            entry_map: Dict[int, Tuple[int, int, int]] = {
                0: (0, 0, 65535),
                5: (1, off_obj5, 0),
                xref_objnum: (1, off_xref, 0),
            }
            xref_data = _xref_stream_data(idx, entry_map)
            dictx = f"/Type /XRef /Size {xref_objnum + 1} /W [ 1 4 2 ] /Index {_fmt_index(idx)} /Root 1 0 R /Prev {prev_off}"
            b.add_stream_obj(xref_objnum, dictx, xref_data)

            b.write(b"startxref\n" + str(off_xref).encode("ascii") + b"\n%%EOF\n")

            prev_off = off_xref
            prev_xref_objnum = xref_objnum

        return bytes(b.buf)