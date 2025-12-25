import os
from typing import List


class Solution:
    def solve(self, src_path: str) -> bytes:
        high_obj = 200000

        def xref_entry(t: int, f2: int, f3: int) -> bytes:
            return bytes((t,)) + int(f2).to_bytes(4, "big", signed=False) + int(f3).to_bytes(2, "big", signed=False)

        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        obj6 = b"<< /Type /Pages /Kids [] /Count 0 >>"
        obj_hi = b"<<>>"
        objects_data = obj6 + b" " + obj_hi
        ofs0 = 0
        ofs1 = len(obj6) + 1
        index_part = f"6 {ofs0} {high_obj} {ofs1} ".encode("ascii")
        first = len(index_part)
        objstm_data = index_part + objects_data
        objstm_len = len(objstm_data)

        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 6 0 R >>\nendobj\n"

        obj5_dict = f"<< /Type /ObjStm /N 2 /First {first} /Length {objstm_len} >>".encode("ascii")
        obj5 = b"5 0 obj\n" + obj5_dict + b"\nstream\n" + objstm_data + b"\nendstream\nendobj\n"

        parts: List[bytes] = [header]
        offset1 = sum(len(p) for p in parts)
        parts.append(obj1)
        offset5 = sum(len(p) for p in parts)
        parts.append(obj5)
        offset8 = sum(len(p) for p in parts)

        xref_data = b"".join(
            [
                xref_entry(0, 0, 65535),            # 0
                xref_entry(1, offset1, 0),          # 1
                xref_entry(0, 0, 0),                # 2
                xref_entry(0, 0, 0),                # 3
                xref_entry(0, 0, 0),                # 4
                xref_entry(1, offset5, 0),          # 5
                xref_entry(2, 5, 0),                # 6 (in objstm 5, index 0)
                xref_entry(0, 0, 0),                # 7
                xref_entry(1, offset8, 0),          # 8 (xref stream itself)
            ]
        )
        xref_len = len(xref_data)

        obj8_dict = (
            f"<< /Type /XRef /Size 9 /W [1 4 2] /Index [0 9] /Root 1 0 R /Length {xref_len} >>"
        ).encode("ascii")
        obj8 = b"8 0 obj\n" + obj8_dict + b"\nstream\n" + xref_data + b"\nendstream\nendobj\n"
        parts.append(obj8)

        trailer = b"startxref\n" + str(offset8).encode("ascii") + b"\n%%EOF\n"
        parts.append(trailer)

        return b"".join(parts)