from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, List


def _be_bytes(val: int, n: int) -> bytes:
    return val.to_bytes(n, "big", signed=False)


def _xref_entry(w: Tuple[int, int, int], t: int, f2: int, f3: int) -> bytes:
    w0, w1, w2 = w
    return _be_bytes(t, w0) + _be_bytes(f2, w1) + _be_bytes(f3, w2)


@dataclass
class _PDFBuilder:
    buf: bytearray
    offsets: Dict[int, int]

    def __init__(self) -> None:
        self.buf = bytearray()
        self.offsets = {}

    def _write(self, b: bytes) -> None:
        self.buf.extend(b)

    def add_obj(self, num: int, body: bytes) -> None:
        self.offsets[num] = len(self.buf)
        self._write(f"{num} 0 obj\n".encode("ascii"))
        self._write(body)
        if not body.endswith(b"\n"):
            self._write(b"\n")
        self._write(b"endobj\n")

    def add_stream_obj(self, num: int, dict_src: bytes, stream_data: bytes) -> None:
        self.offsets[num] = len(self.buf)
        self._write(f"{num} 0 obj\n".encode("ascii"))
        self._write(dict_src)
        if not dict_src.endswith(b"\n"):
            self._write(b"\n")
        self._write(b"stream\n")
        self._write(stream_data)
        self._write(b"\nendstream\nendobj\n")

    def add_startxref_eof(self, xref_offs: int) -> None:
        self._write(b"startxref\n")
        self._write(str(xref_offs).encode("ascii"))
        self._write(b"\n%%EOF\n")


def _make_objstm(objects: List[Tuple[int, bytes]]) -> Tuple[bytes, int, int]:
    # objects: list of (objnum, body_bytes) where body_bytes have no trailing newline needed
    bodies = [b for _, b in objects]
    objdata = b"\n".join(bodies)
    offs = []
    cur = 0
    for i, b in enumerate(bodies):
        offs.append(cur)
        if i != len(bodies) - 1:
            cur += len(b) + 1
        else:
            cur += len(b)
    pairs_parts = []
    for (num, _), off in zip(objects, offs):
        pairs_parts.append(f"{num} {off}".encode("ascii"))
    pairs = b" ".join(pairs_parts) + b"\n"
    first = len(pairs)
    stream = pairs + objdata
    length = len(stream)
    return stream, first, length


def _make_xref_stream_data(
    size: int,
    w: Tuple[int, int, int],
    entries: Dict[int, Tuple[int, int, int]],
    default_free: Tuple[int, int, int] = (0, 0, 0),
) -> bytes:
    # entries maps objnum -> (type, field2, field3)
    out = bytearray()
    for i in range(size):
        if i in entries:
            t, f2, f3 = entries[i]
        else:
            t, f2, f3 = default_free
        out.extend(_xref_entry(w, t, f2, f3))
    return bytes(out)


def _make_xref_stream_data_indexed(
    w: Tuple[int, int, int],
    index_ranges: List[Tuple[int, int]],
    entries: Dict[int, Tuple[int, int, int]],
    default_free: Tuple[int, int, int] = (0, 0, 0),
) -> bytes:
    out = bytearray()
    for start, count in index_ranges:
        for objnum in range(start, start + count):
            if objnum in entries:
                t, f2, f3 = entries[objnum]
            else:
                t, f2, f3 = default_free
            out.extend(_xref_entry(w, t, f2, f3))
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        b = _PDFBuilder()
        b._write(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")

        # Base revision objects (uncompressed minimal page tree)
        b.add_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>\n")
        b.add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n")
        b.add_obj(3, b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>\n")
        b.add_obj(4, b"<< /Length 0 >>\nstream\nendstream\n")

        # Object stream with compressed objects 6,7,8 (used as /Root in later update)
        obj6 = b"<< /Type /Catalog /Pages 7 0 R >>"
        obj7 = b"<< /Type /Pages /Kids [8 0 R] /Count 1 >>"
        obj8 = b"<< /Type /Page /Parent 7 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << >> >>"
        objstm_data, first, objstm_len = _make_objstm([(6, obj6), (7, obj7), (8, obj8)])
        dict10 = f"<< /Type /ObjStm /N 3 /First {first} /Length {objstm_len} >>\n".encode("ascii")
        b.add_stream_obj(10, dict10, objstm_data)

        # Base xref stream object 5
        # We'll set /Size to 20 to include update xref objects as free initially.
        size = 20
        w = (1, 4, 2)
        base_entries: Dict[int, Tuple[int, int, int]] = {
            0: (0, 0, 65535),
            1: (1, 0, 0),  # filled after offsets known
            2: (1, 0, 0),
            3: (1, 0, 0),
            4: (1, 0, 0),
            5: (1, 0, 0),  # xref itself
            6: (2, 10, 0),
            7: (2, 10, 1),
            8: (2, 10, 2),
            10: (1, 0, 0),
            11: (0, 0, 0),
            12: (0, 0, 0),
        }

        # We'll add xref 5 after computing offsets for known objects; but need xref 5 offset too.
        # Create placeholder xref 5 with correct /Length computed after offsets are known.
        # Compute entries once we know offset of object 5.
        # We'll build xref 5 only after setting its offset.
        xref5_offs = len(b.buf)
        b.offsets[5] = xref5_offs

        # Fill offsets for base entries
        base_entries[1] = (1, b.offsets[1], 0)
        base_entries[2] = (1, b.offsets[2], 0)
        base_entries[3] = (1, b.offsets[3], 0)
        base_entries[4] = (1, b.offsets[4], 0)
        base_entries[10] = (1, b.offsets[10], 0)
        base_entries[5] = (1, xref5_offs, 0)

        xref5_data = _make_xref_stream_data(size, w, base_entries, default_free=(0, 0, 0))
        dict5 = (
            b"<< /Type /XRef /Size " + str(size).encode("ascii") +
            b" /W [1 4 2] /Index [0 " + str(size).encode("ascii") +
            b"] /Root 1 0 R /Length " + str(len(xref5_data)).encode("ascii") + b" >>\n"
        )
        b.add_stream_obj(5, dict5, xref5_data)
        b.add_startxref_eof(b.offsets[5])

        # Update 1: xref stream object 11 with /Prev -> base xref, update /Root -> 6 0 R
        # Include entries for 0, 6, 11 so object 6 is found in the newest section.
        xref11_offs = len(b.buf)
        b.offsets[11] = xref11_offs
        index11 = [(0, 1), (6, 1), (11, 1)]
        entries11 = {
            0: (0, 0, 65535),
            6: (2, 10, 0),
            11: (1, xref11_offs, 0),
        }
        xref11_data = _make_xref_stream_data_indexed(w, index11, entries11, default_free=(0, 0, 0))
        dict11 = (
            b"<< /Type /XRef /Size " + str(size).encode("ascii") +
            b" /W [1 4 2] /Index [0 1 6 1 11 1] /Root 6 0 R /Prev " +
            str(b.offsets[5]).encode("ascii") + b" /Length " +
            str(len(xref11_data)).encode("ascii") + b" >>\n"
        )
        b.add_stream_obj(11, dict11, xref11_data)
        b.add_startxref_eof(b.offsets[11])

        # Update 2: xref stream object 12 with /Prev -> xref11, /Root -> 6 0 R
        xref12_offs = len(b.buf)
        b.offsets[12] = xref12_offs
        index12 = [(0, 1), (6, 1), (12, 1)]
        entries12 = {
            0: (0, 0, 65535),
            6: (2, 10, 0),
            12: (1, xref12_offs, 0),
        }
        xref12_data = _make_xref_stream_data_indexed(w, index12, entries12, default_free=(0, 0, 0))
        dict12 = (
            b"<< /Type /XRef /Size " + str(size).encode("ascii") +
            b" /W [1 4 2] /Index [0 1 6 1 12 1] /Root 6 0 R /Prev " +
            str(b.offsets[11]).encode("ascii") + b" /Length " +
            str(len(xref12_data)).encode("ascii") + b" >>\n"
        )
        b.add_stream_obj(12, dict12, xref12_data)
        b.add_startxref_eof(b.offsets[12])

        return bytes(b.buf)