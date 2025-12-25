import os
from typing import List, Tuple, Optional


class Solution:
    def _mk_indirect_obj(self, objnum: int, body: bytes) -> bytes:
        if not body.endswith(b"\n"):
            body += b"\n"
        return f"{objnum} 0 obj\n".encode("ascii") + body + b"endobj\n"

    def _mk_stream_obj(self, objnum: int, dict_entries: str, data: bytes) -> bytes:
        d = f"<< {dict_entries} /Length {len(data)} >>\n".encode("ascii")
        body = d + b"stream\n" + data + b"endstream\n"
        return self._mk_indirect_obj(objnum, body)

    def _mk_objstm(self, objnum: int, contained: List[Tuple[int, bytes]]) -> bytes:
        # contained: list of (objnum, serialized_object_bytes) where each serialized object is a PDF object body (e.g., "<<...>>")
        objs = []
        for _, ob in contained:
            if not ob.endswith(b"\n"):
                ob += b"\n"
            objs.append(ob)
        offsets = []
        off = 0
        for ob in objs:
            offsets.append(off)
            off += len(ob)
        index_parts = []
        for (onum, _), o in zip(contained, offsets):
            index_parts.append(f"{onum} {o}")
        index = (" ".join(index_parts) + "\n").encode("ascii")
        first = len(index)
        stream_data = index + b"".join(objs)
        entries = f"/Type /ObjStm /N {len(contained)} /First {first} /Length {len(stream_data)}"
        return self._mk_stream_obj(objnum, entries, stream_data)

    def _mk_xref_stream(
        self,
        objnum: int,
        size: int,
        offsets_type1: dict,
        type2_entries: dict,
        free_objs: set,
        root_ref: str,
        prev: Optional[int],
        self_offset: int,
    ) -> bytes:
        # W [1 4 2], big-endian fields
        # offsets_type1: {objnum: offset}
        # type2_entries: {objnum: (objstm_num, index)}
        # free_objs: set of objnums that should be type 0
        # Any obj without explicit setting defaults to free.
        entries = bytearray()
        for onum in range(size):
            if onum == 0:
                t = 0
                f2 = 0
                f3 = 65535
            elif onum in type2_entries:
                t = 2
                f2, f3 = type2_entries[onum]
            elif onum in offsets_type1:
                t = 1
                f2 = offsets_type1[onum]
                f3 = 0
            elif onum in free_objs:
                t = 0
                f2 = 0
                f3 = 0
            else:
                t = 0
                f2 = 0
                f3 = 0
            entries.append(t & 0xFF)
            entries.extend(int(f2).to_bytes(4, "big", signed=False))
            entries.extend(int(f3).to_bytes(2, "big", signed=False))

        dparts = [
            "/Type /XRef",
            f"/Size {size}",
            "/W [1 4 2]",
            f"/Index [0 {size}]",
            f"/Root {root_ref}",
            f"/Length {len(entries)}",
        ]
        if prev is not None:
            dparts.insert(4, f"/Prev {prev}")
        dict_str = "<< " + " ".join(dparts) + " >>\n"
        body = dict_str.encode("ascii") + b"stream\n" + bytes(entries) + b"\nendstream\n"
        return f"{objnum} 0 obj\n".encode("ascii") + body + b"endobj\n"

    def solve(self, src_path: str) -> bytes:
        # Build a multi-revision PDF with object streams and multiple xref entries for the same object id
        # across xref stream /Prev chain.
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"

        parts = [header]
        offsets = {}

        def add_obj(objnum: int, body: bytes):
            offsets[objnum] = sum(len(p) for p in parts)
            parts.append(self._mk_indirect_obj(objnum, body))

        def add_obj_stream(objnum: int, entries: str, data: bytes):
            offsets[objnum] = sum(len(p) for p in parts)
            parts.append(self._mk_stream_obj(objnum, entries, data))

        def add_objstm(objnum: int, contained: List[Tuple[int, bytes]]):
            offsets[objnum] = sum(len(p) for p in parts)
            parts.append(self._mk_objstm(objnum, contained))

        # Core objects (revision 1)
        add_obj(1, b"<< /Type /Catalog /Pages 2 0 R /Foo 10 0 R >>")
        add_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        add_obj(
            3,
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] "
            b"/Resources << /Font << /F1 6 0 R >> >> /Contents 4 0 R >>",
        )

        content = b"BT /F1 12 Tf 10 10 Td (Hello) Tj ET\n"
        add_obj_stream(4, "", content)

        # Object stream 5 contains objects 6 and 10
        obj6_v1 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        obj10 = b"<< /Bar 1 /Baz (x) >>\n"
        add_objstm(5, [(6, obj6_v1), (10, obj10)])

        # Revision 1 XRef stream (object 7), Size up to 10 -> 11 entries
        size1 = 11
        free1 = {8, 9}
        type2_1 = {6: (5, 0), 10: (5, 1)}
        xref1_objnum = 7
        xref1_offset = sum(len(p) for p in parts)
        offsets[xref1_objnum] = xref1_offset

        offsets_type1_1 = {
            1: offsets[1],
            2: offsets[2],
            3: offsets[3],
            4: offsets[4],
            5: offsets[5],
            7: xref1_offset,
        }
        parts.append(
            self._mk_xref_stream(
                objnum=xref1_objnum,
                size=size1,
                offsets_type1=offsets_type1_1,
                type2_entries=type2_1,
                free_objs=free1,
                root_ref="1 0 R",
                prev=None,
                self_offset=xref1_offset,
            )
        )
        parts.append(f"startxref\n{xref1_offset}\n%%EOF\n".encode("ascii"))

        # Revision 2: add object stream 8 with updated object 6; xref stream 11
        obj6_v2 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\n"
        add_objstm(8, [(6, obj6_v2)])

        size2 = 12  # up to object 11
        free2 = {9}
        type2_2 = {6: (8, 0), 10: (5, 1)}
        xref2_objnum = 11
        xref2_offset = sum(len(p) for p in parts)
        offsets[xref2_objnum] = xref2_offset

        offsets_type1_2 = {
            1: offsets[1],
            2: offsets[2],
            3: offsets[3],
            4: offsets[4],
            5: offsets[5],
            7: offsets[7],
            8: offsets[8],
            11: xref2_offset,
        }
        parts.append(
            self._mk_xref_stream(
                objnum=xref2_objnum,
                size=size2,
                offsets_type1=offsets_type1_2,
                type2_entries=type2_2,
                free_objs=free2,
                root_ref="1 0 R",
                prev=xref1_offset,
                self_offset=xref2_offset,
            )
        )
        parts.append(f"startxref\n{xref2_offset}\n%%EOF\n".encode("ascii"))

        # Revision 3: add object stream 12 with another updated object 6; xref stream 15
        obj6_v3 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman >>\n"
        add_objstm(12, [(6, obj6_v3)])

        size3 = 16  # up to object 15
        free3 = {9, 13, 14}
        type2_3 = {6: (12, 0), 10: (5, 1)}
        xref3_objnum = 15
        xref3_offset = sum(len(p) for p in parts)
        offsets[xref3_objnum] = xref3_offset

        offsets_type1_3 = {
            1: offsets[1],
            2: offsets[2],
            3: offsets[3],
            4: offsets[4],
            5: offsets[5],
            7: offsets[7],
            8: offsets[8],
            11: offsets[11],
            12: offsets[12],
            15: xref3_offset,
        }
        parts.append(
            self._mk_xref_stream(
                objnum=xref3_objnum,
                size=size3,
                offsets_type1=offsets_type1_3,
                type2_entries=type2_3,
                free_objs=free3,
                root_ref="1 0 R",
                prev=xref2_offset,
                self_offset=xref3_offset,
            )
        )
        parts.append(f"startxref\n{xref3_offset}\n%%EOF\n".encode("ascii"))

        return b"".join(parts)