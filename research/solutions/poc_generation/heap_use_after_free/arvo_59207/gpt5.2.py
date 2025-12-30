import os
from typing import List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        return self._build_pdf()

    @staticmethod
    def _u_be(n: int, w: int) -> bytes:
        return int(n).to_bytes(w, "big", signed=False)

    @classmethod
    def _xref_entry(cls, t: int, f2: int, f3: int, w: Tuple[int, int, int] = (1, 4, 2)) -> bytes:
        return cls._u_be(t, w[0]) + cls._u_be(f2, w[1]) + cls._u_be(f3, w[2])

    @staticmethod
    def _pdf_obj(num: int, gen: int, body: bytes) -> bytes:
        return (f"{num} {gen} obj\n".encode("ascii") + body + b"\nendobj\n")

    @staticmethod
    def _pdf_stream_obj(num: int, gen: int, dict_src: bytes, data: bytes) -> bytes:
        body = dict_src + b"\nstream\n" + data + b"\nendstream"
        return Solution._pdf_obj(num, gen, body)

    @classmethod
    def _build_objstm(cls) -> Tuple[bytes, int]:
        obj1 = b"<< /Type /Catalog /Pages 2 0 R >>\n"
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1 1] /Resources <<>> >>\n"
        objs = [obj1, obj2, obj3]

        offsets = []
        cur = 0
        for b in objs:
            offsets.append(cur)
            cur += len(b)

        header = f"1 {offsets[0]} 2 {offsets[1]} 3 {offsets[2]}\n".encode("ascii")
        first = len(header)
        data = header + b"".join(objs)
        return data, first

    @classmethod
    def _build_pdf(cls) -> bytes:
        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        # Object 4: ObjStm containing objects 1,2,3
        objstm_data, first = cls._build_objstm()
        obj4_dict = f"<< /Type /ObjStm /N 3 /First {first} /Length {len(objstm_data)} >>".encode("ascii")
        obj4 = cls._pdf_stream_obj(4, 0, obj4_dict, objstm_data)

        parts = [header, obj4]
        off4 = len(header)

        # Object 5: xref stream (Size 6: objects 0..5)
        off5 = sum(len(p) for p in parts)
        w = (1, 4, 2)
        xref5 = b"".join([
            cls._xref_entry(0, 0, 65535, w),      # 0 free
            cls._xref_entry(2, 4, 0, w),          # 1 in objstm 4 index 0
            cls._xref_entry(2, 4, 1, w),          # 2 in objstm 4 index 1
            cls._xref_entry(2, 4, 2, w),          # 3 in objstm 4 index 2
            cls._xref_entry(1, off4, 0, w),       # 4 objstm
            cls._xref_entry(1, off5, 0, w),       # 5 xref stream itself
        ])
        obj5_dict = f"<< /Type /XRef /Size 6 /Root 1 0 R /W[1 4 2] /Length {len(xref5)} >>".encode("ascii")
        obj5 = cls._pdf_stream_obj(5, 0, obj5_dict, xref5)

        parts.append(obj5)

        # Object 6: incremental xref stream (Size 7: objects 0..6), /Prev -> obj5 offset
        off6 = sum(len(p) for p in parts)
        xref6 = b"".join([
            cls._xref_entry(0, 0, 65535, w),
            cls._xref_entry(2, 4, 0, w),
            cls._xref_entry(2, 4, 1, w),
            cls._xref_entry(2, 4, 2, w),
            cls._xref_entry(1, off4, 0, w),
            cls._xref_entry(1, off5, 0, w),
            cls._xref_entry(1, off6, 0, w),
        ])
        obj6_dict = f"<< /Type /XRef /Size 7 /Root 1 0 R /Prev {off5} /W[1 4 2] /Length {len(xref6)} >>".encode("ascii")
        obj6 = cls._pdf_stream_obj(6, 0, obj6_dict, xref6)
        parts.append(obj6)

        # Final startxref points to the latest xref stream object (6)
        trailer = f"startxref\n{off6}\n%%EOF\n".encode("ascii")
        parts.append(trailer)

        return b"".join(parts)