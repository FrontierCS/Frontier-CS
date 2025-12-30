import os
from typing import Dict, List, Tuple


class Solution:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _be(n: int, w: int) -> bytes:
        if n < 0:
            n = 0
        return int(n).to_bytes(w, "big", signed=False)

    @classmethod
    def _xref_entry(cls, t: int, f2: int, f3: int) -> bytes:
        return bytes((t & 0xFF,)) + cls._be(f2, 4) + cls._be(f3, 2)

    @staticmethod
    def _pdf_obj(num: int, content: bytes) -> bytes:
        return (f"{num} 0 obj\n").encode("ascii") + content + b"\nendobj\n"

    @staticmethod
    def _stream_obj_content(dict_bytes: bytes, stream_data: bytes) -> bytes:
        return dict_bytes + b"\nstream\n" + stream_data + b"\nendstream"

    @classmethod
    def _make_objstm(cls, contained: List[Tuple[int, bytes]]) -> Tuple[bytes, int]:
        bodies: List[bytes] = []
        offsets: List[int] = []
        cur = 0
        for _, body in contained:
            offsets.append(cur)
            bodies.append(body)
            cur += len(body) + 1  # newline separator
        body_section = b"\n".join(bodies) + b"\n"
        header_parts: List[bytes] = []
        for (objnum, _), off in zip(contained, offsets):
            header_parts.append(f"{objnum} {off} ".encode("ascii"))
        header = b"".join(header_parts)
        stream_data = header + body_section
        first = len(header)
        return stream_data, first

    @classmethod
    def _make_xref_stream(
        cls,
        size: int,
        index_ranges: List[Tuple[int, int]],
        root_ref: bytes,
        prev_offset: int | None,
        uncompressed_offsets: Dict[int, int],
        compressed_map: Dict[int, Tuple[int, int]],
        xref_obj_num: int,
        xref_obj_offset: int,
    ) -> Tuple[bytes, bytes]:
        entries: List[int] = []
        for start, count in index_ranges:
            for i in range(count):
                entries.append(start + i)

        data_parts: List[bytes] = []
        for objnum in entries:
            if objnum == 0:
                data_parts.append(cls._xref_entry(0, 0, 65535))
                continue
            if objnum == xref_obj_num:
                data_parts.append(cls._xref_entry(1, xref_obj_offset, 0))
                continue
            if objnum in uncompressed_offsets:
                data_parts.append(cls._xref_entry(1, uncompressed_offsets[objnum], 0))
                continue
            if objnum in compressed_map:
                osn, idx = compressed_map[objnum]
                data_parts.append(cls._xref_entry(2, osn, idx))
                continue
            data_parts.append(cls._xref_entry(0, 0, 0))

        stream_data = b"".join(data_parts)
        index_str = " ".join(f"{a} {b}" for a, b in index_ranges).encode("ascii")
        dict_parts = [
            b"<< /Type /XRef",
            b" /Size " + str(size).encode("ascii"),
            b" /W [1 4 2]",
            b" /Index [" + index_str + b"]",
            b" /Root " + root_ref,
            b" /Length " + str(len(stream_data)).encode("ascii"),
        ]
        if prev_offset is not None:
            dict_parts.append(b" /Prev " + str(prev_offset).encode("ascii"))
        dict_bytes = b"".join(dict_parts) + b" >>"
        return dict_bytes, stream_data

    def solve(self, src_path: str) -> bytes:
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"

        root_ref = b"1 0 R"

        base_objects: Dict[int, bytes] = {}

        base_objects[1] = b"<< /Type /Catalog /Pages 2 0 R /X 6 0 R /Y 6 0 R >>"
        base_objects[2] = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
        base_objects[3] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 5 0 R /Resources << >> >>"

        contents_dict = b"<< /Length 0 >>"
        base_objects[5] = self._stream_obj_content(contents_dict, b"")

        # Revisions with object streams redefining object 6; each introduces a unique object to keep older streams live.
        # rev0: objstm 4 has objects 6 and 7; xref 8
        # rev1: objstm 9 has objects 6 and 10; xref 12
        # rev2: objstm 13 has objects 6 and 11; xref 16
        # rev3: objstm 17 has objects 6 and 14; xref 20
        # rev4: objstm 21 has objects 6 and 15; xref 24
        revisions = [
            (4, 8, 7),
            (9, 12, 10),
            (13, 16, 11),
            (17, 20, 14),
            (21, 24, 15),
        ]

        # Build PDF incrementally
        pdf = bytearray()
        pdf += header

        offsets: Dict[int, int] = {}
        uncompressed_offsets: Dict[int, int] = {}

        # Base objects 1,2,3,5
        for objnum in [1, 2, 3, 5]:
            offsets[objnum] = len(pdf)
            uncompressed_offsets[objnum] = offsets[objnum]
            pdf += self._pdf_obj(objnum, base_objects[objnum])

        prev_xref_offset: int | None = None
        active_obj6_refs: List[int] = [7]
        # Keep a stable list to reference all unique objects from the final object 6
        unique_objs: List[int] = [7, 10, 11, 14, 15]

        # For each revision, append object stream and xref stream + startxref/EOF
        for rev_index, (objstm_num, xref_num, uniq_obj) in enumerate(revisions):
            if rev_index == 0:
                # Initial revision includes object stream 4 in main body before first xref
                pass
            else:
                # Incremental updates: new objects appended after previous EOF
                pass

            # Create object 6 dictionary for this revision
            # Final revision references all unique objects to ensure older object streams are needed.
            if rev_index == len(revisions) - 1:
                refs = unique_objs
            else:
                refs = unique_objs[: max(1, min(len(unique_objs), rev_index + 1))]
                if uniq_obj not in refs:
                    refs = refs + [uniq_obj]
                # Ensure it includes earlier objects too
                refs = sorted(set(refs), key=lambda x: unique_objs.index(x) if x in unique_objs else 999)

            parts = [b"<< /Rev " + str(rev_index).encode("ascii")]
            # Add multiple references to exercise writer traversals
            for k, r in enumerate(refs):
                key = b" /K" + str(k).encode("ascii")
                parts.append(key + b" " + str(r).encode("ascii") + b" 0 R")
            # Add some extra structure
            parts.append(b" /Arr [")
            for r in refs:
                parts.append(str(r).encode("ascii") + b" 0 R ")
            parts.append(b"]")
            parts.append(b" /Str (abcdefg)")
            parts.append(b" >>")
            obj6_body = b"".join(parts)

            uniq_body = b"<< /Unique " + str(uniq_obj).encode("ascii") + b" /Text (u" + str(uniq_obj).encode("ascii") + b") >>"

            # Object stream contains object 6 and uniq_obj
            objstm_stream_data, first = self._make_objstm([(6, obj6_body), (uniq_obj, uniq_body)])
            objstm_dict = (
                b"<< /Type /ObjStm"
                + b" /N 2"
                + b" /First "
                + str(first).encode("ascii")
                + b" /Length "
                + str(len(objstm_stream_data)).encode("ascii")
                + b" >>"
            )
            objstm_content = self._stream_obj_content(objstm_dict, objstm_stream_data)

            # Place object stream in file
            offsets[objstm_num] = len(pdf)
            uncompressed_offsets[objstm_num] = offsets[objstm_num]
            pdf += self._pdf_obj(objstm_num, objstm_content)

            # Build xref stream for this revision
            if rev_index == 0:
                # Full xref covering 0..xref_num (8)
                size = xref_num + 1  # 9
                index_ranges = [(0, size)]
                # compressed map: 6->objstm 4 idx0; 7->objstm4 idx1
                compressed_map = {6: (objstm_num, 0), 7: (objstm_num, 1)}
            else:
                # Sparse xref
                size = xref_num + 1
                # include 0, 6, uniq_obj, objstm_num, xref_num
                # build increasing /Index
                targets = sorted({0, 6, uniq_obj, objstm_num, xref_num})
                index_ranges = []
                i = 0
                while i < len(targets):
                    start = targets[i]
                    cnt = 1
                    j = i + 1
                    while j < len(targets) and targets[j] == targets[j - 1] + 1:
                        cnt += 1
                        j += 1
                    index_ranges.append((start, cnt))
                    i = j
                compressed_map = {6: (objstm_num, 0), uniq_obj: (objstm_num, 1)}

            xref_offset = len(pdf)
            # xref dict needs its own offset, which is known now
            xref_dict, xref_stream_data = self._make_xref_stream(
                size=size,
                index_ranges=index_ranges,
                root_ref=root_ref,
                prev_offset=prev_xref_offset,
                uncompressed_offsets=uncompressed_offsets,
                compressed_map=compressed_map,
                xref_obj_num=xref_num,
                xref_obj_offset=xref_offset,
            )
            xref_content = self._stream_obj_content(xref_dict, xref_stream_data)
            offsets[xref_num] = xref_offset
            uncompressed_offsets[xref_num] = xref_offset
            pdf += self._pdf_obj(xref_num, xref_content)

            # startxref and EOF for this revision
            pdf += b"startxref\n" + str(xref_offset).encode("ascii") + b"\n%%EOF\n"

            prev_xref_offset = xref_offset

        return bytes(pdf)