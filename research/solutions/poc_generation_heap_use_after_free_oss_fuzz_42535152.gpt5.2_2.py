import struct
from typing import List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        def make_obj(num: int, body: bytes) -> bytes:
            if not body.endswith(b"\n"):
                body += b"\n"
            return f"{num} 0 obj\n".encode("ascii") + body + b"endobj\n"

        def make_stream_obj(num: int, dict_body: bytes, stream_data: bytes) -> bytes:
            if not dict_body.endswith(b"\n"):
                dict_body += b"\n"
            return (
                f"{num} 0 obj\n".encode("ascii")
                + dict_body
                + b"stream\n"
                + stream_data
                + b"\nendstream\nendobj\n"
            )

        def pack_xref_entries(w: Tuple[int, int, int], entries: List[Tuple[int, int, int]]) -> bytes:
            wt, w2, w3 = w
            out = bytearray()
            for t, f2, f3 in entries:
                if wt != 1:
                    raise ValueError("unexpected W for type")
                out.append(t & 0xFF)
                out += int(f2).to_bytes(w2, "big", signed=False)
                out += int(f3).to_bytes(w3, "big", signed=False)
            return bytes(out)

        def make_objstm(objstm_num: int, contained_objnum: int, contained_obj: bytes) -> bytes:
            if not contained_obj.endswith(b"\n"):
                contained_obj += b"\n"
            header = f"{contained_objnum} 0\n".encode("ascii")
            first = len(header)
            data = header + contained_obj
            d = (
                b"<< /Type /ObjStm /N 1 /First "
                + str(first).encode("ascii")
                + b" /Length "
                + str(len(data)).encode("ascii")
                + b" >>\n"
            )
            return make_stream_obj(objstm_num, d, data)

        def make_xref_stream_obj(
            xref_num: int,
            size: int,
            root_obj: int,
            index_pairs: List[Tuple[int, int]],
            prev: Optional[int],
            entries: List[Tuple[int, int, int]],
            offsets_for_entry_type1: Optional[dict] = None,
        ) -> bytes:
            w = (1, 4, 2)
            xref_data = pack_xref_entries(w, entries)
            idx = b"[ " + b" ".join((f"{a} {b}".encode("ascii") for a, b in index_pairs)) + b" ]"
            d = bytearray()
            d += b"<< /Type /XRef"
            d += b" /Size " + str(size).encode("ascii")
            d += b" /Root " + str(root_obj).encode("ascii") + b" 0 R"
            d += b" /W [1 4 2]"
            d += b" /Index " + idx
            if prev is not None:
                d += b" /Prev " + str(prev).encode("ascii")
            d += b" /Length " + str(len(xref_data)).encode("ascii")
            d += b" >>\n"
            return make_stream_obj(xref_num, bytes(d), xref_data)

        # Build a multi-revision incremental-update PDF where object 5 is repeatedly redefined
        # as a compressed object in different object streams. This creates multiple entries for
        # the same object id across preserved object streams.
        revisions = 8  # total revisions including the base one
        # Object numbering plan:
        # base: 1,2,3,4(objstm1),5(compressed),6(contents),7(xref1)
        # updates i=2..R: objstm even starting at 8, xref odd = objstm+1
        objstm_nums = [4] + [8 + 2 * (i - 2) for i in range(2, revisions + 1)]
        xref_nums = [7] + [n + 1 for n in objstm_nums[1:]]

        header = b"%PDF-1.7\n%\xE2\xE3\xCF\xD3\n"

        # Catalog references all object streams to ensure they are reachable even with GC.
        custom_arr = b"[ " + b" ".join((f"{n} 0 R".encode("ascii") for n in objstm_nums)) + b" ]"
        catalog = (
            b"<< /Type /Catalog /Pages 2 0 R /Outlines 5 0 R /Custom "
            + custom_arr
            + b" /PageMode /UseOutlines >>\n"
        )
        pages = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        page = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << >> /Contents 6 0 R >>\n"

        # Base outlines object (object 5) is in objstm 4 initially.
        outlines_v1 = b"<< /Type /Outlines /Count 0 /Rev 1 >>\n"

        contents_data = b"q\nQ\n"
        contents = b"<< /Length " + str(len(contents_data)).encode("ascii") + b" >>\n"

        buf = bytearray()
        buf += header

        offsets = {}

        def append_and_record(num: int, obj_bytes: bytes):
            offsets[num] = len(buf)
            buf.extend(obj_bytes)

        append_and_record(1, make_obj(1, catalog))
        append_and_record(2, make_obj(2, pages))
        append_and_record(3, make_obj(3, page))
        append_and_record(objstm_nums[0], make_objstm(objstm_nums[0], 5, outlines_v1))
        append_and_record(6, make_stream_obj(6, contents, contents_data))

        # XRef stream 1 (object 7)
        offset_xref1 = len(buf)
        offsets[xref_nums[0]] = offset_xref1
        size1 = 8
        entries1 = [
            (0, 0, 65535),                 # 0
            (1, offsets[1], 0),            # 1
            (1, offsets[2], 0),            # 2
            (1, offsets[3], 0),            # 3
            (1, offsets[objstm_nums[0]], 0),  # 4
            (2, objstm_nums[0], 0),        # 5 compressed in objstm 4
            (1, offsets[6], 0),            # 6
            (1, offset_xref1, 0),          # 7 (self)
        ]
        xref1_obj = make_xref_stream_obj(
            xref_nums[0],
            size1,
            1,
            [(0, 8)],
            None,
            entries1,
        )
        buf.extend(xref1_obj)
        buf.extend(b"startxref\n" + str(offset_xref1).encode("ascii") + b"\n%%EOF\n")

        prev_xref_off = offset_xref1

        # Incremental updates: redefine object 5 in a new object stream each time.
        for rev in range(2, revisions + 1):
            objstm_n = objstm_nums[rev - 1]
            xref_n = xref_nums[rev - 1]

            outlines = (b"<< /Type /Outlines /Count 0 /Rev " + str(rev).encode("ascii") + b" >>\n")
            objstm_obj = make_objstm(objstm_n, 5, outlines)

            append_and_record(objstm_n, objstm_obj)

            offset_xref = len(buf)
            offsets[xref_n] = offset_xref

            max_obj = xref_n
            size = max_obj + 1

            # /Index includes: object 0, object 5 override, and the two new objects (objstm and xref itself)
            index_pairs = [(0, 1), (5, 1), (objstm_n, 2)]

            entries = [
                (0, 0, 65535),          # 0
                (2, objstm_n, 0),        # 5 compressed in new objstm
                (1, offsets[objstm_n], 0),  # objstm_n offset
                (1, offset_xref, 0),     # xref_n offset (self)
            ]

            xref_obj = make_xref_stream_obj(
                xref_n,
                size,
                1,
                index_pairs,
                prev_xref_off,
                entries,
            )
            buf.extend(xref_obj)
            buf.extend(b"startxref\n" + str(offset_xref).encode("ascii") + b"\n%%EOF\n")

            prev_xref_off = offset_xref

        return bytes(buf)